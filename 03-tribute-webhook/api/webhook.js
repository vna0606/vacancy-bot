const crypto = require('crypto');

module.exports.config = {
  api: {
    bodyParser: false,
  },
};

async function readRawBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(typeof chunk === 'string' ? Buffer.from(chunk) : chunk);
  }
  return Buffer.concat(chunks);
}

function verifySignature(rawBody, signature, apiKey) {
  if (!signature || !apiKey) return false;
  const expected = crypto.createHmac('sha256', apiKey).update(rawBody).digest('hex');
  const sigBuf = Buffer.from(signature, 'utf8');
  const expBuf = Buffer.from(expected, 'utf8');
  if (sigBuf.length !== expBuf.length) return false;
  return crypto.timingSafeEqual(sigBuf, expBuf);
}

function tursoArg(value) {
  if (value === null || value === undefined) return { type: 'null' };
  if (typeof value === 'number') return { type: 'integer', value: String(value) };
  return { type: 'text', value: String(value) };
}

async function tursoExecute(sql, args = []) {
  const url = `${process.env.TURSO_URL.replace('libsql://', 'https://')}/v2/pipeline`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.TURSO_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      requests: [
        { type: 'execute', stmt: { sql, args: args.map(tursoArg) } },
        { type: 'close' },
      ],
    }),
  });
  const data = await resp.json();
  const result = data.results[0];
  if (result.type === 'error') {
    throw new Error(`Turso error: ${JSON.stringify(result.error)}`);
  }
  return result.response.result;
}

async function ensureSchema() {
  await tursoExecute(`CREATE TABLE IF NOT EXISTS donations (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type           TEXT NOT NULL,
    donation_request_id  INTEGER,
    donation_name        TEXT,
    telegram_user_id     INTEGER,
    telegram_username    TEXT,
    amount               INTEGER,
    currency             TEXT,
    period               TEXT,
    anonymously          INTEGER,
    message              TEXT,
    webhook_created_at   TEXT,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_type, donation_request_id, telegram_user_id, amount, period, webhook_created_at)
  )`);
}

async function insertDonation(fields) {
  const sql = `INSERT INTO donations
    (event_type, donation_request_id, donation_name, telegram_user_id,
     telegram_username, amount, currency, period, anonymously, message, webhook_created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`;
  const args = [
    fields.eventType, fields.donationRequestId, fields.donationName, fields.telegramUserId,
    fields.telegramUsername, fields.amount, fields.currency, fields.period,
    fields.anonymously ? 1 : 0, fields.message, fields.webhookCreatedAt,
  ];
  try {
    await tursoExecute(sql, args);
    return true;
  } catch (e) {
    if (String(e.message).toUpperCase().includes('UNIQUE')) return false;
    throw e;
  }
}

async function sendTelegramMessage(chatId, text) {
  const url = `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/sendMessage`;
  await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text }),
  });
}

function fmtAmount(amount, currency) {
  return `${(amount / 100).toFixed(2)} ${(currency || '').toUpperCase()}`;
}

const DONATION_EVENTS = new Set(['new_donation', 'recurrent_donation', 'cancelled_donation']);

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ status: 'error', message: 'method not allowed' });
    return;
  }

  const rawBody = await readRawBody(req);
  const signature = req.headers['trbt-signature'];

  if (!verifySignature(rawBody, signature, process.env.TRIBUTE_API_KEY)) {
    console.warn('[tribute-webhook] invalid signature, rejected');
    res.status(401).json({ status: 'error', message: 'invalid signature' });
    return;
  }

  let event;
  try {
    event = JSON.parse(rawBody.toString('utf8'));
  } catch {
    res.status(400).json({ status: 'error', message: 'bad json' });
    return;
  }

  const name = event.name;
  const payload = event.payload || {};
  const webhookCreatedAt = event.created_at || '';

  if (event.test_event) {
    console.log('[tribute-webhook] test ping received, ok');
    res.status(200).json({ status: 'ok' });
    return;
  }

  if (DONATION_EVENTS.has(name)) {
    await ensureSchema();
    const isNew = await insertDonation({
      eventType: name,
      donationRequestId: payload.donation_request_id,
      donationName: payload.donation_name,
      telegramUserId: payload.telegram_user_id,
      telegramUsername: payload.telegram_username,
      amount: payload.amount,
      currency: payload.currency,
      period: payload.period,
      anonymously: payload.anonymously,
      message: payload.message,
      webhookCreatedAt,
    });

    const tgId = payload.telegram_user_id;
    if (isNew && !payload.anonymously && tgId) {
      const sumStr = fmtAmount(payload.amount, payload.currency);
      let text = null;
      if (name === 'new_donation') {
        text = `Спасибо за поддержку — ${sumStr} 🙏❤️\nЭто очень помогает развитию бота!`;
      } else if (name === 'recurrent_donation') {
        text = `Спасибо за регулярную поддержку — ${sumStr} в этом периоде 🙏❤️`;
      }
      if (text) {
        try {
          await sendTelegramMessage(tgId, text);
        } catch (e) {
          console.error('[tribute-webhook] failed to send thank-you:', e);
        }
      }
    }
  } else {
    console.log(`[tribute-webhook] unhandled event: ${name}`);
  }

  res.status(200).json({ status: 'ok' });
};
