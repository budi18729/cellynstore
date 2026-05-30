from utils.db import get_conn

def next_ticket_number():
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE counter SET count = count + 1 WHERE id = 1')
    conn.commit()
    c.execute('SELECT count FROM counter WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row["count"]
