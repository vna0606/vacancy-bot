// === Дашборд статистики vacancy-notifier ===
// Настройка перед использованием:
// 1. В редакторе Apps Script: Файл → Свойства проекта → Свойства скрипта (Script Properties)
//    добавить два свойства:
//      TURSO_URL   — значение из 01-bot/.env (вида libsql://xxx-yyy.turso.io)
//      TURSO_TOKEN — значение из 01-bot/.env
// 2. Сохранить, перезагрузить таблицу — в меню появится пункт «📊 Обновить статистику»

const STACK_DIRECTIONS = [
  'Python', 'Backend', 'Frontend', 'ML/AI', 'Mobile',
  'DevOps', 'QA', 'Data', 'FullStack',
];

const MONTH_NAMES = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
];

function formatMonth_(ym) {
  const [year, month] = ym.split('-');
  return MONTH_NAMES[parseInt(month, 10) - 1] + ' ' + year;
}

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📊 Статистика бота')
    .addItem('Обновить данные', 'updateStats')
    .addToUi();
}

function turso_(sql) {
  const props = PropertiesService.getScriptProperties();
  const url = props.getProperty('TURSO_URL').replace(/^libsql:/, 'https:');
  const token = props.getProperty('TURSO_TOKEN');

  const response = UrlFetchApp.fetch(url + '/v2/pipeline', {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + token },
    payload: JSON.stringify({
      requests: [
        { type: 'execute', stmt: { sql: sql } },
        { type: 'close' },
      ],
    }),
  });

  const result = JSON.parse(response.getContentText());
  const cols = result.results[0].response.result.cols.map(c => c.name);
  const rows = result.results[0].response.result.rows.map(row =>
    row.map(cell => (cell.type === 'null' ? null : cell.value))
  );
  return rows.map(row => {
    const obj = {};
    cols.forEach((name, i) => (obj[name] = row[i]));
    return obj;
  });
}

function updateStats() {
  const rows = turso_('SELECT stacks, notify_enabled, created_at FROM users');

  let total = 0;
  let active = 0;
  const activeByDirection = {};
  const allByDirection = {};
  const byMonth = {}; // 'YYYY-MM' -> новых регистраций
  const sortedMonths = [];

  rows.forEach(r => {
    total++;
    let stacks = [];
    try { stacks = r.stacks ? JSON.parse(r.stacks) : []; } catch (e) { stacks = []; }

    stacks.forEach(d => { allByDirection[d] = (allByDirection[d] || 0) + 1; });

    if (String(r.notify_enabled) === '1' && stacks.length) {
      active++;
      stacks.forEach(d => { activeByDirection[d] = (activeByDirection[d] || 0) + 1; });
    }

    const month = (r.created_at || '').slice(0, 7); // 'YYYY-MM'
    if (month) {
      if (!(month in byMonth)) sortedMonths.push(month);
      byMonth[month] = (byMonth[month] || 0) + 1;
    }
  });

  sortedMonths.sort();

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Статистика') || ss.insertSheet('Статистика');
  sheet.clear();
  sheet.getCharts().forEach(c => sheet.removeChart(c));

  const HEADER_BG = '#4a86e8';
  const HEADER_FONT = '#ffffff';
  const HIGHLIGHT_BG = '#eaf1fb';

  const styleHeaderRow = (r, width) => {
    sheet.getRange(r, 1, 1, width).setFontWeight('bold').setBackground(HEADER_BG).setFontColor(HEADER_FONT);
  };
  const styleTable = (startRow, numRows, width) => {
    sheet.getRange(startRow, 1, numRows, width).setBorder(true, true, true, true, true, true);
  };

  const percent = total ? Math.round((active / total) * 100) : 0;
  sheet.getRange('A1').setValue('Обновлено: ' + Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd HH:mm')).setFontStyle('italic');

  // --- Сводка (главные показатели) ---
  let row = 3;
  const summaryTitleRow = row;
  sheet.getRange(row, 1, 1, 3).merge().setValue('📈 Общие показатели')
    .setHorizontalAlignment('center');
  styleHeaderRow(row, 3);
  row++;
  const summaryDataStartRow = row;
  sheet.getRange(row, 1).setValue('Всего пользователей');
  sheet.getRange(row, 2).setValue(total).setFontSize(14).setFontWeight('bold');
  row++;
  sheet.getRange(row, 1).setValue('Получают рассылку');
  sheet.getRange(row, 2).setValue(active).setFontSize(14).setFontWeight('bold');
  sheet.getRange(row, 3).setValue(percent + '%').setFontSize(14).setFontWeight('bold');
  row++;
  sheet.getRange(summaryDataStartRow, 1, 2, 3).setBackground(HIGHLIGHT_BG);
  styleTable(summaryTitleRow, 3, 3);

  // --- Разбивка по направлениям (таблица + круговая диаграмма справа) ---
  row += 2;
  const directionHeaderRow = row;
  sheet.getRange(row, 1).setValue('Направление');
  sheet.getRange(row, 2).setValue('Получают рассылку');
  sheet.getRange(row, 3).setValue('Все пользователи');
  styleHeaderRow(row, 3);
  row++;
  STACK_DIRECTIONS.forEach(d => {
    sheet.getRange(row, 1).setValue(d);
    sheet.getRange(row, 2).setValue(activeByDirection[d] || 0);
    sheet.getRange(row, 3).setValue(allByDirection[d] || 0);
    row++;
  });
  styleTable(directionHeaderRow, STACK_DIRECTIONS.length + 1, 3);

  const pieChart = sheet.newChart()
    .setChartType(Charts.ChartType.PIE)
    .addRange(sheet.getRange(directionHeaderRow, 1, STACK_DIRECTIONS.length + 1, 1))
    .addRange(sheet.getRange(directionHeaderRow, 3, STACK_DIRECTIONS.length + 1, 1))
    .setPosition(summaryTitleRow, 5, 0, 0)
    .setOption('title', 'Разбивка по направлениям (все пользователи)')
    .setOption('width', 480)
    .setOption('height', 300)
    .build();
  sheet.insertChart(pieChart);

  // --- Динамика по месяцам: таблица слева направо (месяц = столбец) ---
  row += 2;
  const monthsHeaderRow = row;
  const monthsWidth = sortedMonths.length + 1;
  sortedMonths.forEach((m, i) => sheet.getRange(row, 2 + i).setValue(formatMonth_(m)));
  styleHeaderRow(row, monthsWidth);
  row++;
  sheet.getRange(row, 1).setValue('Новых регистраций');
  sortedMonths.forEach((m, i) => sheet.getRange(row, 2 + i).setValue(byMonth[m]));
  row++;
  sheet.getRange(row, 1).setValue('Всего пользователей');
  let cumulative = 0;
  sortedMonths.forEach((m, i) => {
    cumulative += byMonth[m];
    sheet.getRange(row, 2 + i).setValue(cumulative);
  });
  styleTable(monthsHeaderRow, 3, monthsWidth);

  sheet.setFrozenRows(1);
  sheet.setColumnWidths(1, 3, 180);
  if (monthsWidth > 3) sheet.autoResizeColumns(4, monthsWidth - 3);

  // Комбинированная диаграмма: новые пользователи (столбцы) + общая динамика (линия)
  if (sortedMonths.length > 0) {
    const dynamicsChart = sheet.newChart()
      .setChartType(Charts.ChartType.COMBO)
      .addRange(sheet.getRange(monthsHeaderRow, 1, 3, monthsWidth))
      .setTransposeRowsAndColumns(true)
      .setOption('title', 'Динамика пользователей по месяцам')
      .setOption('series', {
        0: { type: 'bars', label: 'Новых за месяц', targetAxisIndex: 0 },
        1: { type: 'line', label: 'Всего пользователей', targetAxisIndex: 1 },
      })
      .setOption('width', 700)
      .setOption('height', 320)
      .setPosition(monthsHeaderRow + 5, 1, 0, 0)
      .build();
    sheet.insertChart(dynamicsChart);
  }
}
