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
  const res = result.results[0];
  if (!res || res.type === 'error') {
    throw new Error('Turso error: ' + JSON.stringify(res && res.error ? res.error : res) + '\nSQL: ' + sql);
  }
  const cols = res.response.result.cols.map(c => c.name);
  const rows = res.response.result.rows.map(row =>
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

  updateFunnel_();
}

function updateFunnel_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Воронка') || ss.insertSheet('Воронка');
  sheet.clear();
  sheet.getCharts().forEach(c => sheet.removeChart(c));

  const HEADER_BG = '#4a86e8';
  const HEADER_FONT = '#ffffff';
  const HIGHLIGHT_BG = '#eaf1fb';
  const GREEN_BG = '#d9ead3';
  const YELLOW_BG = '#fff2cc';
  const RED_BG = '#fce5cd';

  const styleHeader = (r, c, w) => {
    sheet.getRange(r, c, 1, w)
      .setFontWeight('bold').setBackground(HEADER_BG).setFontColor(HEADER_FONT);
  };
  const border = (r, c, rows, cols) => {
    sheet.getRange(r, c, rows, cols).setBorder(true, true, true, true, true, true);
  };

  sheet.getRange('A1').setValue('Обновлено: ' + Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd HH:mm')).setFontStyle('italic');

  // --- Воронка активации ---
  const users = turso_('SELECT notify_enabled, stacks, stacks_set_at FROM users');
  const totalUsers = users.length;
  const stackSet = users.filter(u => u.stacks_set_at !== null).length;
  const activeUsers = users.filter(u => String(u.notify_enabled) === '1').length;
  const sentRows = turso_('SELECT COUNT(DISTINCT user_tg_id) AS cnt FROM sent_notifications');
  const gotVacancy = parseInt(sentRows[0].cnt || 0, 10);

  let row = 3;
  sheet.getRange(row, 1, 1, 4).merge().setValue('🎯 Воронка активации')
    .setHorizontalAlignment('center');
  styleHeader(row, 1, 4);
  row++;

  const funnelHeaderRow = row;
  sheet.getRange(row, 1).setValue('Этап');
  sheet.getRange(row, 2).setValue('Пользователей');
  sheet.getRange(row, 3).setValue('% от зарегистрированных');
  sheet.getRange(row, 4).setValue('% от предыдущего');
  styleHeader(row, 1, 4);
  row++;

  const funnelData = [
    ['Зарегистрировались', totalUsers, 100, 100],
    ['Настроили стек', stackSet, pct_(stackSet, totalUsers), pct_(stackSet, totalUsers)],
    ['Уведомления включены', activeUsers, pct_(activeUsers, totalUsers), pct_(activeUsers, stackSet)],
    ['Получили хотя бы одну вакансию', gotVacancy, pct_(gotVacancy, totalUsers), pct_(gotVacancy, activeUsers)],
  ];
  const funnelBGs = [GREEN_BG, GREEN_BG, YELLOW_BG, YELLOW_BG];

  funnelData.forEach(([label, count, pctTotal, pctPrev], i) => {
    sheet.getRange(row, 1).setValue(label);
    sheet.getRange(row, 2).setValue(count).setFontWeight('bold').setFontSize(13);
    sheet.getRange(row, 3).setValue(pctTotal + '%');
    sheet.getRange(row, 4).setValue(pctPrev + '%');
    sheet.getRange(row, 1, 1, 4).setBackground(funnelBGs[i]);
    row++;
  });
  border(funnelHeaderRow, 1, funnelData.length + 1, 4);

  // --- Почему выключены уведомления ---
  row += 2;
  const disabledRows = turso_(
    "SELECT disabled_reason, COUNT(*) AS cnt FROM users WHERE notify_enabled = 0 GROUP BY disabled_reason"
  );
  const disabledTotal = disabledRows.reduce((s, r) => s + parseInt(r.cnt, 10), 0);

  sheet.getRange(row, 1, 1, 3).merge().setValue('❌ Причины отключения уведомлений')
    .setHorizontalAlignment('center');
  styleHeader(row, 1, 3);
  row++;

  const disabledHeaderRow = row;
  sheet.getRange(row, 1).setValue('Причина');
  sheet.getRange(row, 2).setValue('Пользователей');
  sheet.getRange(row, 3).setValue('% от отключённых');
  styleHeader(row, 1, 3);
  row++;

  const REASON_LABELS = {
    'manual':     '👤 Выключил сам',
    'blocked':    '🚫 Заблокировал бота',
    'non_member': '🔒 Не в сообществе',
    null:         '❓ Причина неизвестна',
  };
  const reasonBGs = {
    'manual': YELLOW_BG, 'blocked': RED_BG, 'non_member': RED_BG, null: HIGHLIGHT_BG,
  };

  disabledRows.forEach(r => {
    const cnt = parseInt(r.cnt, 10);
    const label = REASON_LABELS[r.disabled_reason] || r.disabled_reason || '❓ Причина неизвестна';
    const bg = reasonBGs[r.disabled_reason] || HIGHLIGHT_BG;
    sheet.getRange(row, 1).setValue(label);
    sheet.getRange(row, 2).setValue(cnt).setFontWeight('bold');
    sheet.getRange(row, 3).setValue(pct_(cnt, disabledTotal) + '%');
    sheet.getRange(row, 1, 1, 3).setBackground(bg);
    row++;
  });
  if (disabledRows.length === 0) {
    sheet.getRange(row, 1).setValue('Нет данных');
    row++;
  }
  border(disabledHeaderRow, 1, Math.max(disabledRows.length, 1) + 1, 3);

  // --- Активность: живые пользователи ---
  row += 2;
  const activity = turso_(
    "SELECT " +
    "COUNT(CASE WHEN last_seen_at >= datetime('now','-7 days') THEN 1 END) AS w7, " +
    "COUNT(CASE WHEN last_seen_at >= datetime('now','-30 days') THEN 1 END) AS m30, " +
    "COUNT(CASE WHEN last_seen_at IS NULL THEN 1 END) AS never " +
    "FROM users"
  )[0];

  sheet.getRange(row, 1, 1, 3).merge().setValue('🟢 Активность пользователей')
    .setHorizontalAlignment('center');
  styleHeader(row, 1, 3);
  row++;
  const actHeaderRow = row;
  sheet.getRange(row, 1).setValue('Период');
  sheet.getRange(row, 2).setValue('Пользователей');
  sheet.getRange(row, 3).setValue('% от всех');
  styleHeader(row, 1, 3);
  row++;

  const actData = [
    ['Активны за последние 7 дней', parseInt(activity.w7 || 0, 10)],
    ['Активны за последние 30 дней', parseInt(activity.m30 || 0, 10)],
    ['Никогда не заходили после регистрации', parseInt(activity.never || 0, 10)],
  ];
  const actBGs = [GREEN_BG, YELLOW_BG, RED_BG];

  actData.forEach(([label, count], i) => {
    sheet.getRange(row, 1).setValue(label);
    sheet.getRange(row, 2).setValue(count).setFontWeight('bold');
    sheet.getRange(row, 3).setValue(pct_(count, totalUsers) + '%');
    sheet.getRange(row, 1, 1, 3).setBackground(actBGs[i]);
    row++;
  });
  border(actHeaderRow, 1, actData.length + 1, 3);

  // --- Топ событий из user_events ---
  row += 2;
  let eventRows = [];
  try {
    eventRows = turso_(
      "SELECT event, COUNT(*) AS cnt FROM user_events GROUP BY event ORDER BY cnt DESC"
    );
  } catch (e) {
    // таблица user_events ещё не создана — пропускаем
  }

  if (eventRows.length > 0) {
    sheet.getRange(row, 1, 1, 2).merge().setValue('📋 События (всего за всё время)')
      .setHorizontalAlignment('center');
    styleHeader(row, 1, 2);
    row++;
    const evHeaderRow = row;
    sheet.getRange(row, 1).setValue('Событие');
    sheet.getRange(row, 2).setValue('Количество');
    styleHeader(row, 1, 2);
    row++;
    eventRows.forEach(r => {
      sheet.getRange(row, 1).setValue(r.event);
      sheet.getRange(row, 2).setValue(parseInt(r.cnt, 10)).setFontWeight('bold');
      row++;
    });
    border(evHeaderRow, 1, eventRows.length + 1, 2);
  }

  // --- Источники трафика (ref_source) ---
  row += 2;
  let sourceRows = [];
  try {
    sourceRows = turso_(
      "SELECT COALESCE(ref_source, 'direct') AS src, COUNT(*) AS cnt " +
      "FROM users GROUP BY src ORDER BY cnt DESC"
    );
  } catch (e) {
    // колонка ещё не создана — пропускаем
  }

  if (sourceRows.length > 0) {
    const srcTotal = sourceRows.reduce((s, r) => s + parseInt(r.cnt, 10), 0);
    sheet.getRange(row, 1, 1, 3).merge().setValue('🔗 Источники трафика')
      .setHorizontalAlignment('center');
    styleHeader(row, 1, 3);
    row++;
    const srcHeaderRow = row;
    sheet.getRange(row, 1).setValue('Источник');
    sheet.getRange(row, 2).setValue('Пользователей');
    sheet.getRange(row, 3).setValue('% от всех');
    styleHeader(row, 1, 3);
    row++;
    sourceRows.forEach(r => {
      const cnt = parseInt(r.cnt, 10);
      sheet.getRange(row, 1).setValue(r.src);
      sheet.getRange(row, 2).setValue(cnt).setFontWeight('bold');
      sheet.getRange(row, 3).setValue(pct_(cnt, srcTotal) + '%');
      row++;
    });
    border(srcHeaderRow, 1, sourceRows.length + 1, 3);
  }

  sheet.setColumnWidth(1, 280);
  sheet.setColumnWidth(2, 150);
  sheet.setColumnWidth(3, 200);
  sheet.setColumnWidth(4, 200);
  sheet.setFrozenRows(1);
}

function pct_(part, total) {
  if (!total) return 0;
  return Math.round((part / total) * 100);
}
