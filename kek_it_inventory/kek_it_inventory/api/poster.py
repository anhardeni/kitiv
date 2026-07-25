import frappe
import requests
import json
from frappe import _
from kek_it_inventory.kek_it_inventory.api.ledger import update_ledger

def translate_customs_error(error_msg):
	"""
	Translates technical/JSON error messages from Bea Cukai/SINSW API 
	into clear, human-readable Indonesian operational instructions.
	"""
	if not error_msg:
		return "Terjadi kesalahan pabean tidak dikenal."
	
	err = str(error_msg).lower()
	
	# 1. Credential & Auth Errors
	if "insw-key" in err or "unique-key" in err or "auth" in err or "key" in err and "invalid" in err:
		return "❌ **KESALAHAN OTENTIKASI**: Kredensial API (`x-insw-key` atau `x-unique-key`) tidak valid atau kedaluwarsa. Silakan periksa pengaturan pada **KEK API Credential** Anda."
	
	# 2. UOM / Satuan Errors
	if "uom" in err or "satuan" in err or "kd_satuan" in err or "kdsatuan" in err or "kdsat" in err:
		return "⚠️ **PEMETAAN SATUAN ERROR**: Kode Satuan (UOM) barang belum dipetakan. Silakan daftarkan pemetaan satuan di modul **KEK Ref Unit** Anda."
		
	# 3. Item Code / Mapping Errors
	if "item" in err or "barang" in err or "kdbarang" in err or "kd_barang" in err or "not match mapped" in err:
		return "⚠️ **PEMETAAN BARANG ERROR**: Kode barang internal ERPNext belum dipetakan ke Kode Barang Bea Cukai. Silakan daftarkan pemetaan barang di modul **KEK Item Mapping** Anda."
		
	# 4. NPWP / NIB Errors
	if "npwp" in err or "nib" in err:
		return "❌ **PROFIL PERUSAHAAN ERROR**: Nomor NPWP atau NIB perusahaan tidak cocok dengan profil terdaftar Bea Cukai. Silakan periksa **KEK Company Profile** Anda."
		
	# 5. Connection & Timeout
	if "connection" in err or "timeout" in err or "max retries" in err or "http" in err and "error" in err:
		return "⚠️ **GANGGUAN KONEKSI**: Koneksi ke server Bea Cukai (SINSW) mengalami gangguan atau *timeout*. Sistem akan mencoba mengirim ulang otomatis beberapa saat lagi. Tidak perlu membatalkan dokumen."
		
	# 6. Fallback (If no specific match, clean the string up slightly for humans)
	return f"❌ **TINDAKAN DIPERLUKAN**: Penolakan dari Bea Cukai/SINSW: {error_msg}"

def get_unique_key(cred):
	"""
	Retrieves the dynamic X-Unique-Key from SINSW.
	"""
	base_url = cred.base_url.strip() if cred.base_url else ""
	if "/api/inventory" in base_url:
		endpoint = f"{base_url.rstrip('/')}/getUniqueKey"
	elif "/api-prod/inventory" in base_url:
		endpoint = f"{base_url.rstrip('/')}/getUniqueKey"
	else:
		endpoint = f"{base_url.rstrip('/')}/api/inventory/getUniqueKey"

	insw_key = cred.get_password("x_insw_key")
	
	try:
		response = requests.get(endpoint, headers={"x-insw-key": insw_key}, timeout=10)
		if response.status_code == 200:
			data = response.json()
			return data.get("data") or data.get("uniqueKey") or data.get("unique_key")
	except Exception as e:
		error_title = f"Failed to fetch KEK Unique Key: {str(e)}"
		frappe.log_error(error_title[:140], "KEK API Error")
	
	return None

def update_reference_doc(doc, status, insw_id=None, error_msg=None):
	"""
	Propagates status back to the source ERPNext document.
	"""
	if doc.erpnext_reference_doctype and doc.erpnext_reference_name:
		try:
			meta = frappe.get_meta(doc.erpnext_reference_doctype)
			update_dict = {}
			if meta.has_field("kek_status"):
				update_dict["kek_status"] = status
			if meta.has_field("kek_transaction"):
				update_dict["kek_transaction"] = doc.name
			if meta.has_field("kek_insw_id"):
				update_dict["kek_insw_id"] = insw_id or ""
			if meta.has_field("kek_error"):
				update_dict["kek_error"] = error_msg or ""
			if meta.has_field("nomor_ppkek") and doc.get("nomor_ppkek"):
				update_dict["nomor_ppkek"] = doc.nomor_ppkek
			if meta.has_field("custom_bc_registration_no") and doc.get("nomor_ppkek"):
				update_dict["custom_bc_registration_no"] = doc.nomor_ppkek
			
			if update_dict:
				frappe.db.set_value(doc.erpnext_reference_doctype, doc.erpnext_reference_name, update_dict, update_modified=False)
		except Exception as e:
			frappe.log_error(f"Failed to update reference doc {doc.erpnext_reference_doctype} {doc.erpnext_reference_name}: {str(e)}", "KEK Reference Update Error")

@frappe.whitelist()
def post_transaction(docname):
	"""
	Posts a KEK Inventory Transaction to SINSW Gateway following KEK PDF standards.
	"""
	doc = frappe.get_doc("KEK Inventory Transaction", docname)
	profile = frappe.get_doc("KEK Company Profile", doc.company_profile)
	
	cred_name = frappe.db.get_value("KEK API Credential", 
		{"company_profile": profile.name, "active": 1}, "name")
	
	if not cred_name:
		frappe.db.set_value("KEK Inventory Transaction", doc.name, "status", "FAILED")
		doc.add_comment("Comment", "❌ No active API Credentials found.")
		update_reference_doc(doc, "FAILED", error_msg="No active API Credentials found.")
		return

	cred = frappe.get_doc("KEK API Credential", cred_name)
	insw_key = cred.get_password("x_insw_key")
	unique_key = get_unique_key(cred) or cred.get_password("x_unique_key")

	# Determine namaEntitas (Supplier for inbound/30, Customer for outbound/31, fallback to company name)
	nama_entitas = profile.company_name
	if doc.erpnext_reference_doctype and doc.erpnext_reference_name:
		if frappe.db.exists(doc.erpnext_reference_doctype, doc.erpnext_reference_name):
			ref_doc = frappe.get_doc(doc.erpnext_reference_doctype, doc.erpnext_reference_name)
			if doc.transaction_type == "30":
				nama_entitas = ref_doc.get("supplier_name") or ref_doc.get("supplier") or nama_entitas
			elif doc.transaction_type == "31":
				nama_entitas = ref_doc.get("customer_name") or ref_doc.get("customer") or nama_entitas

	is_opening_stock = False
	if doc.erpnext_reference_doctype == "Stock Reconciliation" and doc.erpnext_reference_name:
		ref_purpose = frappe.db.get_value("Stock Reconciliation", doc.erpnext_reference_name, "purpose")
		if ref_purpose == "Opening Stock":
			is_opening_stock = True

	# 1. Build Payload
	if is_opening_stock:
		# Format no_kegiatan & tgl_kegiatan
		no_kegiatan = doc.nomor_ppkek or doc.erpnext_reference_name or doc.name
		tgl_keg_dt = doc.tanggal_ppkek or doc.transaction_date
		tgl_kegiatan = ""
		if tgl_keg_dt:
			tgl_kegiatan = frappe.utils.get_datetime(tgl_keg_dt).strftime("%d-%m-%Y %H:%M:%S")
			
		# Format tanggal_declare from Posting Date & Time
		declare_dt_obj = frappe.utils.get_datetime(doc.transaction_date)
		if doc.erpnext_reference_doctype == "Stock Reconciliation" and doc.erpnext_reference_name:
			sr_data = frappe.db.get_value("Stock Reconciliation", doc.erpnext_reference_name, ["posting_date", "posting_time"], as_dict=True)
			if sr_data and sr_data.posting_date:
				post_time = sr_data.posting_time or "00:00:00"
				declare_dt_obj = frappe.utils.get_datetime(f"{sr_data.posting_date} {post_time}")
		
		tanggal_declare = declare_dt_obj.strftime("%d-%m-%Y %H:%M:%S") if declare_dt_obj else ""
		
		barang_saldo = []
		for item in doc.items:
			barang = {
				"kd_kategori_barang": item.category_code or "1",
				"kd_barang": item.customs_item_code,
				"uraian_barang": item.item_name_customs or frappe.db.get_value("KEK Item Mapping", {"customs_item_code": item.customs_item_code}, "customs_item_name") or item.customs_item_code,
				"jumlah": float(item.qty),
				"satuan": item.uom_code,
				"nilai": float(item.amount_idr or 0),
				"tanggal_declare": tanggal_declare
			}
			barang_saldo.append(barang)
			
		payload = {
			"data": {
				"no_kegiatan": no_kegiatan,
				"tgl_kegiatan": tgl_kegiatan,
				"barangSaldo": barang_saldo
			}
		}
	else:
		# 1. Build Nested Payload (Strictly following KEK PDF Structure)
		# Structure: data[] -> kdKegiatan, dokumenKegiatan[] -> barangTransaksi[] -> dokumen[]
		dok_kegiatan = {
			"nomorDokKegiatan": doc.erpnext_reference_name or doc.name,
			"tanggalKegiatan": frappe.utils.formatdate(doc.transaction_date, "dd-mm-yyyy"),
		}
		if doc.transaction_type == "33":
			remarks = None
			if doc.erpnext_reference_doctype and doc.erpnext_reference_name:
				if frappe.db.exists(doc.erpnext_reference_doctype, doc.erpnext_reference_name):
					remarks = frappe.db.get_value(doc.erpnext_reference_doctype, doc.erpnext_reference_name, "remarks")
			dok_kegiatan["keterangan"] = remarks or "Adjustment"
			
		dok_kegiatan.update({
			"namaEntitas": nama_entitas,
			"barangTransaksi": []
		})

		payload = {
			"data": [
				{
					"kdKegiatan": doc.transaction_type, 
					"dokumenKegiatan": [dok_kegiatan]
				}
			]
		}

		
		for item in doc.items:
			barang = {
				"kdKategoriBarang": item.category_code or "1",
				"kdBarang": item.customs_item_code,
				"uraianBarang": item.item_name_customs or frappe.db.get_value("KEK Item Mapping", {"customs_item_code": item.customs_item_code}, "customs_item_name"),
				"jumlah": item.qty,
				"kdSatuan": item.uom_code,
				"nilai": item.amount_idr or 0,
				"dokumen": [] 
			}
			
			# Add nested Customs Documents from child table
			customs_docs = item.get("customs_docs") or frappe.get_all("KEK Item Customs Doc", filters={"parent": item.name}, fields=["*"])
			
			# Auto-heal: If empty but parent transaction has nomor_ppkek, insert them now!
			if not customs_docs and doc.get("nomor_ppkek"):
				doc_code = "040700"
				if doc.transaction_type == "30":
					doc_code = "0407611"
				elif doc.transaction_type == "31":
					doc_code = "0407631"
					
				frappe.get_doc({
					"doctype": "KEK Item Customs Doc",
					"parent": item.name,
					"parenttype": "KEK Inventory Transaction Item",
					"parentfield": "customs_docs",
					"customs_doc_code": doc_code,
					"customs_doc_number": doc.nomor_ppkek,
					"customs_doc_date": doc.tanggal_ppkek or doc.transaction_date
				}).insert(ignore_permissions=True)
				
				# Fetch again after auto-heal
				customs_docs = frappe.get_all("KEK Item Customs Doc", filters={"parent": item.name}, fields=["*"])
				
			for doc_ref in customs_docs:
				is_dict = isinstance(doc_ref, dict)
				barang["dokumen"].append({
					"kodeDokumen": doc_ref.get("customs_doc_code") if is_dict else doc_ref.customs_doc_code,
					"nomorDokumen": doc_ref.get("customs_doc_number") if is_dict else doc_ref.customs_doc_number,
					"tanggalDokumen": frappe.utils.formatdate(doc_ref.get("customs_doc_date") if is_dict else doc_ref.customs_doc_date, "dd-mm-yyyy")
				})
			
			payload["data"][0]["dokumenKegiatan"][0]["barangTransaksi"].append(barang)

	# 2. Execute Request
	headers = {
		"Content-Type": "application/json",
		"x-insw-key": insw_key,
		"x-unique-key": unique_key
	}
	
	# Determine endpoint based on activity (Mapping from doc.transaction_type)
	# Default common endpoint for transactions
	base_url = cred.base_url.strip() if cred.base_url else ""
	if is_opening_stock:
		rel_path = "temp/saldoAwal" if cred.environment == "DUMMY" else "saldoAwal"
		if "/api/inventory" in base_url or "/api-prod/inventory" in base_url:
			endpoint = f"{base_url.rstrip('/')}/{rel_path}"
		else:
			endpoint = f"{base_url.rstrip('/')}/api/inventory/{rel_path}"
	else:
		rel_path = "temp/transaksi" if cred.environment == "DUMMY" else "transaksi"
		if "/api/inventory" in base_url or "/api-prod/inventory" in base_url:
			endpoint = f"{base_url.rstrip('/')}/{rel_path}"
		else:
			endpoint = f"{base_url.rstrip('/')}/api/inventory/{rel_path}"
	
	try:
		request_payload_json = json.dumps(payload, indent=4)
		frappe.db.set_value("KEK Inventory Transaction", doc.name, "request_payload", request_payload_json)
		
		response = requests.post(endpoint, data=json.dumps(payload), headers=headers, timeout=30)
		
		frappe.db.set_value("KEK Inventory Transaction", doc.name, "response_payload", response.text)

		if response.status_code in [200, 201]:
			res_data = response.json()
			
			# PDF Standard: status=true and code="01" indicates success
			if res_data.get("status") is True or res_data.get("code") == "01":
				# Extract dynamic ID if provided by SINSW
				result_data_list = res_data.get("data", {}).get("resultDataTransaksi", [])
				insw_id = None
				if result_data_list:
					insw_id = result_data_list[0].get("idTransaksi")
				
				# Extract and save idBarangTransaksi for each item
				result_barang_list = res_data.get("data", {}).get("resultBarangTransaksi", [])
				if result_barang_list:
					# Create a mapping of kdBarang -> list of idBarangTransaksi
					barang_id_map = {}
					for resp_item in result_barang_list:
						kd_barang = resp_item.get("kdBarang")
						id_barang_txn = resp_item.get("idBarangTransaksi")
						if kd_barang and id_barang_txn:
							if kd_barang not in barang_id_map:
								barang_id_map[kd_barang] = []
							barang_id_map[kd_barang].append(id_barang_txn)
					
					# Assign idBarangTransaksi to doc items sequentially
					consumed_indices = {}
					for item in doc.items:
						kd_barang = item.customs_item_code
						if kd_barang in barang_id_map:
							idx = consumed_indices.get(kd_barang, 0)
							if idx < len(barang_id_map[kd_barang]):
								id_barang_txn = barang_id_map[kd_barang][idx]
								frappe.db.set_value("KEK Inventory Transaction Item", item.name, "id_barang_transaksi_insw", id_barang_txn)
								item.id_barang_transaksi_insw = id_barang_txn
								consumed_indices[kd_barang] = idx + 1
				
				# If is_opening_stock and environment is DUMMY, perform PUT to lock
				if is_opening_stock and cred.environment == "DUMMY":
					if "/api/inventory" in base_url:
						lock_endpoint = f"{base_url.rstrip('/')}/temp/registrasi"
					elif "/api-prod/inventory" in base_url:
						lock_endpoint = f"{base_url.rstrip('/')}/temp/registrasi"
					else:
						lock_endpoint = f"{base_url.rstrip('/')}/api/inventory/temp/registrasi"
					
					try:
						# Send PUT request with empty JSON payload
						put_response = requests.put(lock_endpoint, data=json.dumps({}), headers=headers, timeout=30)
						put_data = {}
						try:
							put_data = put_response.json() if put_response.text else {}
						except Exception:
							pass

						if put_response.status_code in [200, 201] and (put_data.get("status") is True or put_data.get("code") == "01" or not put_data):
							# Successful lock, add comment
							doc.add_comment("Comment", f"🔑 <b>Lock Saldo Awal Success</b>: {put_response.text}")
						else:
							# FAILED lock! Mark transaction as failed instead.
							frappe.db.set_value("KEK Inventory Transaction", doc.name, "status", "FAILED")
							translated_msg = translate_customs_error(f"Lock PUT Error ({put_response.status_code}): {put_response.text}")
							doc.add_comment("Comment", translated_msg)
							update_reference_doc(doc, "FAILED", error_msg=translated_msg)
							return
					except Exception as e:
						frappe.db.set_value("KEK Inventory Transaction", doc.name, "status", "FAILED")
						translated_msg = translate_customs_error(f"Lock PUT Connection Error: {str(e)}")
						doc.add_comment("Comment", translated_msg)
						update_reference_doc(doc, "FAILED", error_msg=translated_msg)
						return

				frappe.db.set_value("KEK Inventory Transaction", doc.name, {
					"status": "SENT",
					"insw_transaksi_id": insw_id
				})
				
				# Extract response message
				res_msg = res_data.get("message")
				if isinstance(res_data.get("data"), dict) and res_data.get("data", {}).get("message"):
					res_msg = res_data.get("data", {}).get("message")
				elif not res_msg and isinstance(res_data.get("data"), str):
					res_msg = res_data.get("data")
				
				success_comment = f"✅ <b>SINSW Response ({res_data.get('code', '01')})</b>: {res_msg or 'Data berhasil diproses.'}"
				doc.add_comment("Comment", success_comment)

				# Update Reference document status
				update_reference_doc(doc, "SENT", insw_id=insw_id)
				
				# Trigger Ledger Update only on successful report
				update_ledger(doc.name)
				
				# Reset failure count
				if cred.failure_count > 0:
					frappe.db.set_value("KEK API Credential", cred.name, "failure_count", 0)
			else:
				frappe.db.set_value("KEK Inventory Transaction", doc.name, "status", "FAILED")
				msg = res_data.get("message") or "Unknown SINSW error"
				translated_msg = translate_customs_error(msg)
				doc.add_comment("Comment", translated_msg)
				update_reference_doc(doc, "FAILED", error_msg=translated_msg)
				
		else:
			frappe.db.set_value("KEK Inventory Transaction", doc.name, "status", "FAILED")
			error_msg = response.text
			translated_msg = translate_customs_error(error_msg)
			doc.add_comment("Comment", f"❌ API Error ({response.status_code}): {translated_msg}")
			update_reference_doc(doc, "FAILED", error_msg=translated_msg)
			
			# Track failure on credential
			frappe.db.set_value("KEK API Credential", cred.name, "failure_count", cred.failure_count + 1)

	except Exception as e:
		frappe.db.set_value("KEK Inventory Transaction", doc.name, "status", "FAILED")
		translated_msg = translate_customs_error(f"Connection Error: {str(e)}")
		doc.add_comment("Comment", translated_msg)
		update_reference_doc(doc, "FAILED", error_msg=translated_msg)
		frappe.log_error(frappe.get_traceback(), "KEK Integration Connection Error")

def get_update_endpoint(cred):
	"""
	Constructs the correct PUT update URL:
	- Real: {base_url}/transaksi/dokumen
	- Dummy: {base_url}/temp/transaksi/dokumen
	"""
	base_url = cred.base_url.strip() if cred.base_url else ""
	if "/api/inventory" in base_url:
		path = base_url.rstrip('/')
	elif "/api-prod/inventory" in base_url:
		path = base_url.rstrip('/')
	else:
		path = f"{base_url.rstrip('/')}/api/inventory"
		
	if cred.environment == "DUMMY":
		return f"{path}/temp/transaksi/dokumen"
	else:
		return f"{path}/transaksi/dokumen"

@frappe.whitelist()
def update_customs_documents(docname):
	"""
	Sends PUT updates for each item's customs document using idTransaksi and idBarangTransaksi.
	"""
	doc = frappe.get_doc("KEK Inventory Transaction", docname)
	
	if not doc.insw_transaksi_id:
		return "Error: Transaksi belum memiliki ID Transaksi SINSW (insw_transaksi_id)."

	profile = frappe.get_doc("KEK Company Profile", doc.company_profile)
	cred_name = frappe.db.get_value("KEK API Credential", 
		{"company_profile": profile.name, "active": 1}, "name")
	
	if not cred_name:
		return "Error: No active API Credentials found."

	cred = frappe.get_doc("KEK API Credential", cred_name)
	insw_key = cred.get_password("x_insw_key")
	unique_key = get_unique_key(cred) or cred.get_password("x_unique_key")
	
	endpoint = get_update_endpoint(cred)
	headers = {
		"Content-Type": "application/json",
		"x-insw-key": insw_key,
		"x-unique-key": unique_key
	}
	
	success_count = 0
	failure_count = 0
	errors = []

	for item in doc.items:
		if not item.id_barang_transaksi_insw:
			continue
			
		customs_docs = item.get("customs_docs") or frappe.get_all("KEK Item Customs Doc", filters={"parent": item.name}, fields=["*"])
		if not customs_docs:
			continue
			
		doc_ref = customs_docs[0]
		is_dict = isinstance(doc_ref, dict)
		kode_dokumen = doc_ref.get("customs_doc_code") if is_dict else doc_ref.customs_doc_code
		nomor_dokumen = doc_ref.get("customs_doc_number") if is_dict else doc_ref.customs_doc_number
		tanggal_dokumen_raw = doc_ref.get("customs_doc_date") if is_dict else doc_ref.customs_doc_date
		tanggal_dokumen = frappe.utils.formatdate(tanggal_dokumen_raw, "dd-mm-yyyy")

		payload = {
			"idTransaksi": doc.insw_transaksi_id,
			"idBarangTransaksi": item.id_barang_transaksi_insw,
			"kodeDokumen": kode_dokumen,
			"nomorDokumen": nomor_dokumen,
			"tanggalDokumen": tanggal_dokumen
		}
		
		try:
			response = requests.put(endpoint, data=json.dumps(payload), headers=headers, timeout=30)
			if response.status_code in [200, 201]:
				res_data = response.json()
				if res_data.get("status") is True or res_data.get("code") == "01":
					success_count += 1
				else:
					failure_count += 1
					msg = res_data.get("message") or "Unknown error"
					errors.append(f"Barang {item.customs_item_code}: {msg}")
			else:
				failure_count += 1
				errors.append(f"Barang {item.customs_item_code}: HTTP {response.status_code} - {response.text}")
		except Exception as e:
			failure_count += 1
			errors.append(f"Barang {item.customs_item_code}: Connection/System error {str(e)}")
			
	# Update parent ERPNext doc customs registration if success
	if success_count > 0:
		if doc.erpnext_reference_doctype and doc.erpnext_reference_name:
			if frappe.db.exists(doc.erpnext_reference_doctype, doc.erpnext_reference_name):
				update_dict = {}
				meta = frappe.get_meta(doc.erpnext_reference_doctype)
				if meta.has_field("nomor_ppkek") and doc.nomor_ppkek:
					update_dict["nomor_ppkek"] = doc.nomor_ppkek
				if meta.has_field("tanggal_ppkek") and doc.tanggal_ppkek:
					update_dict["tanggal_ppkek"] = doc.tanggal_ppkek
				if meta.has_field("custom_bc_registration_no") and doc.nomor_ppkek:
					update_dict["custom_bc_registration_no"] = doc.nomor_ppkek
				if meta.has_field("custom_bc_registration_date") and doc.tanggal_ppkek:
					update_dict["custom_bc_registration_date"] = doc.tanggal_ppkek
				if meta.has_field("kek_status"):
					update_dict["kek_status"] = "Validated"
				
				if update_dict:
					frappe.db.set_value(doc.erpnext_reference_doctype, doc.erpnext_reference_name, update_dict, update_modified=False)

	# Record audit log comment
	log_msg = f"<b>🔄 Update Info Dokumen Pabean</b><br>"
	log_msg += f"Sukses: {success_count} item | Gagal: {failure_count} item<br>"
	if errors:
		log_msg += f"Detail Kesalahan:<br>" + "<br>".join(errors)
	doc.add_comment("Comment", text=log_msg)
	
	if failure_count == 0 and success_count > 0:
		return "Success"
	elif success_count > 0:
		return f"Partial Success (Success: {success_count}, Failure: {failure_count}). Errors: {', '.join(errors)}"
	else:
		return f"Failed: {', '.join(errors)}"

def process_queue(sync=False):
	"""
	Finds all QUEUED transactions and attempts to post them.
	"""
	queued_txns = frappe.get_all("KEK Inventory Transaction", 
		filters={"status": "QUEUED"},
		fields=["name"]
	)
	
	for txn in queued_txns:
		if sync:
			post_transaction(txn.name)
		else:
			frappe.enqueue(
				"kek_it_inventory.kek_it_inventory.api.poster.post_transaction",
				docname=txn.name,
				queue="long",
				timeout=300
			)





