from utils.db import get_conn

def load_robux_tickets():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM robux_tickets')
    rows = c.fetchall()
    conn.close()
    tickets = {}
    for row in rows:
        tickets[row['channel_id']] = {
            'channel_id': row['channel_id'],
            'user_id': row['user_id'],
            'item_id': row['item_id'],
            'item_name': row['item_name'],
            'robux': row['robux'],
            'rate': row['rate'],
            'total': row['total'],
            'payment_method': row['payment_method'],
            'payment_embed_msg_id': row['payment_embed_msg_id'],
            'paid': bool(row['paid']),
            'admin_id': row['admin_id'],
            'opened_at': row['opened_at'],
            'warned': bool(row['warned']) if row['warned'] is not None else False,
        }
    return tickets

def save_robux_ticket(ticket):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO robux_tickets
        (channel_id, user_id, item_id, item_name, robux, rate, total,
         payment_method, payment_embed_msg_id, paid, admin_id, opened_at, warned)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        ticket['channel_id'],
        ticket['user_id'],
        ticket['item_id'],
        ticket['item_name'],
        ticket['robux'],
        ticket['rate'],
        ticket['total'],
        ticket.get('payment_method'),
        ticket.get('payment_embed_msg_id'),
        1 if ticket.get('paid') else 0,
        ticket.get('admin_id'),
        ticket['opened_at'],
        1 if ticket.get('warned') else 0,
    ))
    conn.commit()
    conn.close()

def delete_robux_ticket(channel_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM robux_tickets WHERE channel_id = ?', (channel_id,))
    conn.commit()
    conn.close()

def save_bot_state(key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO bot_state (key, value) VALUES (?, ?)', (key, str(value)))
    conn.commit()
    conn.close()

def load_bot_state(key):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT value FROM bot_state WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    return row['value'] if row else None
