/**
 * =========================================================================
 * RUANG VISUAL - Google Spreadsheet Executive Formatter & Webhook
 * =========================================================================
 * Script ini berfungsi ganda:
 * 1. Webhook otomatis untuk menerima data dari scraper tanpa campur aduk kolom.
 * 2. Menu interaktif di Google Sheets untuk:
 *    - Menghapus semua tab tambahan yang tidak perlu (hanya sisakan 3 tab).
 *    - Menghapus seluruh emoji dan emoticon dari seluruh sel.
 *    - Mengubah link panjang menjadi teks singkat ber-link (Buka Peta, Chat WA, Lihat Tren, Buka Web).
 *    - Menghapus baris header ganda atau tumpang tindih.
 * =========================================================================
 */

// ─── 1. WEBHOOK RECEIVER (doPost) ──────────────────────────────────────────
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheetName = data.sheet_name || "Radar Prospek";
    var sheet = ss.getSheetByName(sheetName) || ss.insertSheet(sheetName);

    var action = data.action || "append";

    if (action === "replace_all") {
      sheet.clear();
      if (data.headers && data.headers.length > 0) {
        sheet.appendRow(data.headers);
      }
      if (data.rows && data.rows.length > 0) {
        for (var i = 0; i < data.rows.length; i++) {
          sheet.appendRow(sanitizeRow(data.rows[i], sheetName));
        }
      }
      formatSheet(sheet, sheetName);
    } else {
      // Action: append with deduplication based on Column A
      var existingData = sheet.getDataRange().getValues();
      var existingNames = new Set();
      for (var r = 1; r < existingData.length; r++) {
        var val = String(existingData[r][0] || "").trim().toLowerCase();
        if (val) existingNames.add(val);
      }

      var addedCount = 0;
      for (var j = 0; j < data.rows.length; j++) {
        var rawRow = data.rows[j];
        var rowName = String(rawRow[0] || "").trim().toLowerCase();
        if (rowName && !existingNames.has(rowName) &&
            rowName !== "nama bisnis" && rowName !== "entitas bisnis" &&
            rowName !== "nama percetakan" && rowName.indexOf("sinyal") === -1) {
          sheet.appendRow(sanitizeRow(rawRow, sheetName));
          existingNames.add(rowName);
          addedCount++;
        }
      }
      formatSheet(sheet, sheetName);
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "ok",
      sheet: sheetName,
      action: action
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}


// ─── 2. MENU INTERAKTIF DI GOOGLE SHEETS ────────────────────────────────────
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("RUANG VISUAL")
    .addItem("Bersihkan & Rapikan Semua Tab", "cleanAllSheetsData")
    .addItem("Hapus Semua Tab Selain 3 Tab Utama", "hapusSemuaTabKecualiUtama")
    .addSeparator()
    .addItem("Tentang Sistem", "showAbout")
    .addToUi();
}


// ─── 3. HAPUS SEMUA TAB KECUALI TAB UTAMA ───────────────────────────────────
function hapusSemuaTabKecualiUtama() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var tabUtama = ["Radar Prospek", "Matriks Kompetitor", "Market Signals"];

  // 1. Pastikan ketiga tab utama tersedia
  for (var t = 0; t < tabUtama.length; t++) {
    if (!ss.getSheetByName(tabUtama[t])) {
      ss.insertSheet(tabUtama[t]);
    }
  }

  // 2. Hapus semua tab yang bukan bagian dari 3 tab utama
  var sheets = ss.getSheets();
  var terhapus = 0;
  for (var i = 0; i < sheets.length; i++) {
    var sheetName = sheets[i].getName();
    if (tabUtama.indexOf(sheetName) === -1) {
      try {
        ss.deleteSheet(sheets[i]);
        terhapus++;
      } catch (e) {
        // Abaikan jika tidak diizinkan oleh sistem Google
      }
    }
  }

  // 3. Bersihkan data di ketiga tab utama
  cleanAllSheetsData();

  SpreadsheetApp.getUi().alert(
    "Pembersihan Selesai",
    "Berhasil menghapus " + terhapus + " tab tambahan. Hanya 3 tab utama yang dipertahankan: Radar Prospek, Matriks Kompetitor, dan Market Signals.",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}


// ─── 4. BERSIHKAN DATA SELURUH TAB (PURGE EMOJI & RAPIKAN LINK) ────────────
function cleanAllSheetsData() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  // Tab 1: Radar Prospek
  var leadSheet = ss.getSheetByName("Radar Prospek");
  if (leadSheet) {
    cleanTabContent(leadSheet, [
      "Nama Bisnis", "Kategori", "Skor", "Status", "No. WhatsApp",
      "Link WA", "Proyeksi Kebutuhan Cetak", "Alamat", "Rating & Ulasan",
      "Website", "Peta Lokasi", "Tanggal"
    ]);
  }

  // Tab 2: Matriks Kompetitor
  var compSheet = ss.getSheetByName("Matriks Kompetitor");
  if (compSheet) {
    cleanTabContent(compSheet, [
      "Nama Percetakan", "Fokus Layanan Utama", "Kapasitas / Skala",
      "Rating & Ulasan", "No. WhatsApp", "Link WA", "Celah Kualitas",
      "Celah Pelayanan & SOP", "Selling Point RUANG VISUAL", "Website / Maps", "Tanggal Update"
    ]);
  }

  // Tab 3: Market Signals
  var sigSheet = ss.getSheetByName("Market Signals");
  if (sigSheet) {
    cleanTabContent(sigSheet, [
      "Sinyal / Tren Produk", "Platform", "Tingkat Demand",
      "Peluang untuk RUANG VISUAL", "Link Referensi", "Tanggal"
    ]);
  }
}

function cleanTabContent(sheet, correctHeaders) {
  var range = sheet.getDataRange();
  var values = range.getValues();
  var formulas = range.getFormulas();
  if (values.length === 0) return;

  var sheetName = sheet.getName();
  var cleanedRows = [];
  var seenKeys = new Set();

  for (var i = 0; i < values.length; i++) {
    var rowVals = values[i];
    var rowForms = formulas[i];
    var firstCol = String(rowVals[0] || "").trim().toLowerCase();

    // Lewati baris kosong
    if (!firstCol) continue;

    // Lewati baris header yang terulang di tengah data (seperti baris 2)
    if (firstCol === "nama bisnis" || firstCol === "entitas bisnis" ||
        firstCol === "nama percetakan" || firstCol === "nama kompetitor" ||
        firstCol.indexOf("sinyal") !== -1 || firstCol.indexOf("signal") !== -1 ||
        firstCol.indexOf("tren produk") !== -1) {
      continue;
    }

    // Deduplikasi baris berdasarkan kolom pertama
    if (seenKeys.has(firstCol)) {
      continue;
    }
    seenKeys.add(firstCol);

    var cleanRow = [];
    for (var c = 0; c < correctHeaders.length; c++) {
      var cellForm = (c < rowForms.length) ? String(rowForms[c] || "").trim() : "";
      var cellVal = (c < rowVals.length) ? String(rowVals[c] || "").trim() : "";

      // Prioritaskan rumus hyperlink yang sudah ada, jika tidak ada gunakan teks nilai
      var rawCell = cellForm ? cellForm : cellVal;
      var entityName = String(rowVals[0] || "").trim();
      var addressName = (c >= 7 && c < rowVals.length) ? String(rowVals[7] || "").trim() : "";

      var sanitized = sanitizeCell(rawCell, c, sheetName, entityName, addressName);
      cleanRow.push(sanitized);
    }
    cleanedRows.push(cleanRow);
  }

  sheet.clear();
  sheet.appendRow(correctHeaders);
  for (var j = 0; j < cleanedRows.length; j++) {
    sheet.appendRow(cleanedRows[j]);
  }
  formatSheet(sheet, sheetName);
}


// ─── 5. SANITIZER: PENGHAPUS EMOJI & PEMBUAT TEKS SINGKAT BER-LINK ──────────
function sanitizeRow(row, sheetName) {
  var out = [];
  var entityName = String(row[0] || "").trim();
  for (var c = 0; c < row.length; c++) {
    out.push(sanitizeCell(row[c], c, sheetName, entityName, ""));
  }
  return out;
}

function sanitizeCell(content, colIndex, sheetName, entityName, addressName) {
  if (content === null || content === undefined) return "-";
  var str = String(content).trim();
  if (!str) return "-";

  // 1. Hapus SEMUA karakter emoji dan simbol ornamen via rentang unicode murni
  str = str.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]|[\u2600-\u27BF]|[\u2300-\u23FF]|[\u2B50-\u2B55]|[\uFE00-\uFE0F]/g, "").trim();
  str = str.replace(/\s+/g, " ");

  // 2. Koreksi rumus HYPERLINK yang sudah ada
  if (str.indexOf("=HYPERLINK(") === 0) {
    // Hilangkan teks lama dan rapikan label di dalam rumus
    str = str.replace(/Buka Google Maps/gi, "Buka Peta");
    str = str.replace(/Buka GMaps/gi, "Buka Peta");
    str = str.replace(/Chat WhatsApp/gi, "Chat WA");
    str = str.replace(/Hubungi WhatsApp/gi, "Chat WA");
    str = str.replace(/Kunjungi Website/gi, "Buka Web");
    return str;
  }

  // 3. Ubah URL mentah yang panjang menjadi teks singkat ber-link
  if (str.indexOf("http://") === 0 || str.indexOf("https://") === 0) {
    if (str.indexOf("maps.google") !== -1 || str.indexOf("goo.gl/maps") !== -1 || str.indexOf("/maps/") !== -1) {
      return '=HYPERLINK("' + str + '", "Buka Peta")';
    } else if (str.indexOf("tiktok.com") !== -1) {
      return '=HYPERLINK("' + str + '", "Lihat Tren")';
    } else if (str.indexOf("wa.me") !== -1) {
      return '=HYPERLINK("' + str + '", "Chat WA")';
    } else {
      return '=HYPERLINK("' + str + '", "Buka Web")';
    }
  }

  // 4. Khusus kolom Peta Lokasi di Radar Prospek (Kolom K / indeks 10)
  if (sheetName === "Radar Prospek" && colIndex === 10) {
    if (!str || str === "-" || str === "Buka GMaps" || str === "Buka Peta") {
      if (entityName) {
        var query = encodeURIComponent((entityName + " " + addressName + " Makassar").trim());
        return '=HYPERLINK("https://www.google.com/maps/search/?api=1&query=' + query + '", "Buka Peta")';
      }
    }
  }

  // 5. Khusus teks sisa tombol lama tanpa rumus
  if (str === "Buka GMaps" || str === "Buka Peta") {
    if (entityName) {
      var qMap = encodeURIComponent(entityName + " Makassar");
      return '=HYPERLINK("https://www.google.com/maps/search/?api=1&query=' + qMap + '", "Buka Peta")';
    }
    return "Buka Peta";
  }
  if (str === "Lihat Tren") {
    return '=HYPERLINK("https://www.tiktok.com/search?q=' + encodeURIComponent(entityName) + '", "Lihat Tren")';
  }

  return str;
}


// ─── 6. ENGINE FORMAT TAMPILAN (STYLING) ─────────────────────────────────────
function formatSheet(sheet, sheetName) {
  var lastRow = sheet.getLastRow();
  var lastCol = sheet.getLastColumn();
  if (lastRow === 0 || lastCol === 0) return;

  // 1. Freeze Baris 1 (Header tetap diam saat scroll)
  sheet.setFrozenRows(1);

  // 2. Styling Header Baris 1
  var headerRange = sheet.getRange(1, 1, 1, lastCol);
  headerRange.setBackground("#1E293B");     // Slate Dark / Navy Elegan
  headerRange.setFontColor("#FFFFFF");     // Putih
  headerRange.setFontWeight("bold");
  headerRange.setFontFamily("Inter");
  headerRange.setFontSize(10);
  headerRange.setHorizontalAlignment("center");
  headerRange.setVerticalAlignment("middle");
  headerRange.setWrap(true);
  sheet.setRowHeight(1, 38);

  if (lastRow > 1) {
    // 3. Styling Data Rows
    var dataRange = sheet.getRange(2, 1, lastRow - 1, lastCol);
    dataRange.setFontFamily("Inter");
    dataRange.setFontSize(9.5);
    dataRange.setVerticalAlignment("middle");

    // Default row height
    for (var r = 2; r <= lastRow; r++) {
      sheet.setRowHeight(r, 28);
    }

    // 4. Alternating Colors (Zebra Striping)
    for (var r2 = 2; r2 <= lastRow; r2++) {
      var rowRange = sheet.getRange(r2, 1, 1, lastCol);
      if (r2 % 2 === 0) {
        rowRange.setBackground("#FFFFFF");
      } else {
        rowRange.setBackground("#F8FAFC");
      }
    }

    // 5. Alignment spesifik tiap kolom
    sheet.getRange(2, 1, lastRow - 1, 1).setHorizontalAlignment("left"); // Kolom Nama

    if (sheetName === "Radar Prospek") {
      sheet.getRange(2, 2, lastRow - 1, 1).setHorizontalAlignment("center"); // Kategori
      sheet.getRange(2, 3, lastRow - 1, 1).setHorizontalAlignment("center"); // Skor
      sheet.getRange(2, 4, lastRow - 1, 1).setHorizontalAlignment("center"); // Status
      sheet.getRange(2, 5, lastRow - 1, 1).setHorizontalAlignment("center"); // Telp
      sheet.getRange(2, 6, lastRow - 1, 1).setHorizontalAlignment("center"); // Link WA
      sheet.getRange(2, 9, lastRow - 1, 1).setHorizontalAlignment("center"); // Rating
      sheet.getRange(2, 10, lastRow - 1, 1).setHorizontalAlignment("center"); // Website
      sheet.getRange(2, 11, lastRow - 1, 1).setHorizontalAlignment("center"); // Peta
      sheet.getRange(2, 12, lastRow - 1, 1).setHorizontalAlignment("center"); // Tanggal
    } else if (sheetName === "Matriks Kompetitor") {
      sheet.getRange(2, 3, lastRow - 1, 1).setHorizontalAlignment("center"); // Kapasitas
      sheet.getRange(2, 4, lastRow - 1, 1).setHorizontalAlignment("center"); // Rating
      sheet.getRange(2, 5, lastRow - 1, 1).setHorizontalAlignment("center"); // Telp
      sheet.getRange(2, 6, lastRow - 1, 1).setHorizontalAlignment("center"); // Link WA
      sheet.getRange(2, 10, lastRow - 1, 1).setHorizontalAlignment("center"); // Website / Maps
      sheet.getRange(2, 11, lastRow - 1, 1).setHorizontalAlignment("center"); // Tanggal
    } else if (sheetName === "Market Signals") {
      sheet.getRange(2, 2, lastRow - 1, 1).setHorizontalAlignment("center"); // Platform
      sheet.getRange(2, 3, lastRow - 1, 1).setHorizontalAlignment("center"); // Demand
      sheet.getRange(2, 5, lastRow - 1, 1).setHorizontalAlignment("center"); // Link
      sheet.getRange(2, 6, lastRow - 1, 1).setHorizontalAlignment("center"); // Tanggal
    }
  }

  // 6. Auto-fit lebar kolom
  for (var c = 1; c <= lastCol; c++) {
    sheet.autoResizeColumn(c);
    var width = sheet.getColumnWidth(c);
    if (width < 90) sheet.setColumnWidth(c, 90);
    if (width > 350) sheet.setColumnWidth(c, 350);
  }
}

function showAbout() {
  SpreadsheetApp.getUi().alert(
    "RUANG VISUAL Intelligence Pipeline",
    "Spreadsheet ini terhubung secara otomatis dengan Cloud Pipeline RUANG VISUAL di Makassar.\nData diperbarui secara otomatis setiap Senin & Kamis atau saat dijalankan on-demand dari HP.",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}
