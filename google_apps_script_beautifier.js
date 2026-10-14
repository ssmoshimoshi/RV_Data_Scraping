/**
 * =========================================================================
 * RUANG VISUAL - Google Spreadsheet Executive Formatter & Webhook
 * =========================================================================
 * Script ini berfungsi ganda:
 * 1. Webhook otomatis untuk menerima data dari scraper tanpa campur aduk kolom.
 * 2. Menu interaktif di Google Sheets untuk merapikan, mempercantik tampilan,
 *    dan menghapus data duplikat dengan 1 kali klik.
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
          sheet.appendRow(data.rows[i]);
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
        var row = data.rows[j];
        var rowName = String(row[0] || "").trim().toLowerCase();
        // Skip duplicate names or duplicate headers in rows
        if (rowName && !existingNames.has(rowName) && rowName !== "nama bisnis" && rowName !== "entitas bisnis") {
          sheet.appendRow(row);
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
    .addItem("Rapikan & Format Tampilan Tab", "beautifyAllSheets")
    .addItem("Bersihkan Baris Rusak & Duplikat", "cleanCorruptedRows")
    .addSeparator()
    .addItem("Tentang Sistem", "showAbout")
    .addToUi();
}


// ─── 3. RAPAIKAN SELURUH SHEET (BEAUTIFIER) ──────────────────────────────────
function beautifyAllSheets() {
  cleanCorruptedRows();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    formatSheet(sheets[i], sheets[i].getName());
  }
  SpreadsheetApp.getUi().alert("Berhasil", "Seluruh tab telah dirapikan dengan tampilan profesional RUANG VISUAL.", SpreadsheetApp.getUi().ButtonSet.OK);
}


// ─── 4. BERSIHKAN BARIS RUSAK / TUMPANG TINDIH ──────────────────────────────
function cleanCorruptedRows() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  // Tab 1: Radar Prospek
  var leadSheet = ss.getSheetByName("Radar Prospek");
  if (leadSheet) {
    cleanTabHeaders(leadSheet, [
      "Nama Bisnis", "Kategori", "Skor", "Status", "No. WhatsApp",
      "Link WA", "Proyeksi Kebutuhan Cetak", "Alamat", "Rating & Ulasan",
      "Website", "Peta Lokasi", "Tanggal"
    ]);
  }

  // Tab 2: Matriks Kompetitor
  var compSheet = ss.getSheetByName("Matriks Kompetitor");
  if (compSheet) {
    cleanTabHeaders(compSheet, [
      "Nama Percetakan", "Fokus Layanan Utama", "Kapasitas / Skala",
      "Rating & Ulasan", "No. WhatsApp", "Link WA", "Celah Kualitas",
      "Celah Pelayanan & SOP", "Selling Point RUANG VISUAL", "Website / Maps", "Tanggal Update"
    ]);
  }

  // Tab 3: Market Signals
  var sigSheet = ss.getSheetByName("Market Signals");
  if (sigSheet) {
    cleanTabHeaders(sigSheet, [
      "Sinyal / Tren Produk", "Platform", "Tingkat Demand",
      "Peluang untuk RUANG VISUAL", "Link Referensi", "Tanggal"
    ]);
  }
}

function cleanTabHeaders(sheet, correctHeaders) {
  var range = sheet.getDataRange();
  var values = range.getValues();
  if (values.length === 0) return;

  var cleanedRows = [];
  var seenKeys = new Set();

  for (var i = 0; i < values.length; i++) {
    var row = values[i];
    var firstCol = String(row[0] || "").trim().toLowerCase();

    // Skip empty rows or middle header repetitions
    if (!firstCol) continue;
    if (firstCol === "nama bisnis" || firstCol === "entitas bisnis" ||
        firstCol === "nama kompetitor" || firstCol === "sinyal / tren" ||
        firstCol === "signal / tren") {
      continue;
    }

    if (!seenKeys.has(firstCol)) {
      seenKeys.add(firstCol);
      cleanedRows.push(row);
    }
  }

  sheet.clear();
  sheet.appendRow(correctHeaders);
  for (var j = 0; j < cleanedRows.length; j++) {
    sheet.appendRow(cleanedRows[j]);
  }
  formatSheet(sheet, sheet.getName());
}


// ─── 5. ENGINE FORMAT TAMPILAN (STYLING) ─────────────────────────────────────
function formatSheet(sheet, sheetName) {
  var lastRow = sheet.getLastRow();
  var lastCol = sheet.getLastColumn();
  if (lastRow === 0 || lastCol === 0) return;

  // 1. Freeze Baris 1 (Header tetap diam saat scroll)
  sheet.setFrozenRows(1);

  // 2. Styling Header Baris 1
  var headerRange = sheet.getRange(1, 1, 1, lastCol);
  headerRange.setBackground("#1E293B");     // Slate Dark / Elegant Navy
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

    // 4. Alternating Colors (Zebra Striping lembut)
    for (var r = 2; r <= lastRow; r++) {
      var rowRange = sheet.getRange(r, 1, 1, lastCol);
      if (r % 2 === 0) {
        rowRange.setBackground("#FFFFFF");
      } else {
        rowRange.setBackground("#F8FAFC");  // Very soft gray
      }
    }

    // 5. Alignment spesifik tiap kolom
    sheet.getRange(2, 1, lastRow - 1, 1).setHorizontalAlignment("left"); // Nama

    if (sheetName === "Radar Prospek") {
      sheet.getRange(2, 2, lastRow - 1, 1).setHorizontalAlignment("center"); // Kategori
      sheet.getRange(2, 3, lastRow - 1, 1).setHorizontalAlignment("center"); // Skor
      sheet.getRange(2, 4, lastRow - 1, 1).setHorizontalAlignment("center"); // Status
      sheet.getRange(2, 5, lastRow - 1, 1).setHorizontalAlignment("center"); // Telp
      sheet.getRange(2, 6, lastRow - 1, 1).setHorizontalAlignment("center"); // Link WA
      sheet.getRange(2, 9, lastRow - 1, 1).setHorizontalAlignment("center"); // Rating
      sheet.getRange(2, 11, lastRow - 1, 1).setHorizontalAlignment("center"); // Peta
      sheet.getRange(2, 12, lastRow - 1, 1).setHorizontalAlignment("center"); // Tanggal
    } else if (sheetName === "Matriks Kompetitor") {
      sheet.getRange(2, 3, lastRow - 1, 1).setHorizontalAlignment("center"); // Kapasitas
      sheet.getRange(2, 4, lastRow - 1, 1).setHorizontalAlignment("center"); // Rating
      sheet.getRange(2, 5, lastRow - 1, 1).setHorizontalAlignment("center"); // Telp
      sheet.getRange(2, 6, lastRow - 1, 1).setHorizontalAlignment("center"); // Link WA
    }
  }

  // 6. Auto-fit lebar kolom
  for (var c = 1; c <= lastCol; c++) {
    sheet.autoResizeColumn(c);
    var width = sheet.getColumnWidth(c);
    if (width < 90) sheet.setColumnWidth(c, 90);
    if (width > 350) sheet.setColumnWidth(c, 350); // Mencegah kolom terlalu lebar
  }
}

function showAbout() {
  SpreadsheetApp.getUi().alert(
    "RUANG VISUAL Intelligence Pipeline",
    "Spreadsheet ini terhubung secara otomatis dengan Cloud Pipeline RUANG VISUAL di Makassar.\nData diperbarui secara otomatis setiap Senin & Kamis atau saat dijalankan on-demand dari HP.",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}
