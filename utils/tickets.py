import datetime
from utils.db import get_conn

def save_tickets(active_tickets):
    conn = get_conn()
    c = conn.cursor()
    # Pastikan kolom warned ada (safe migration)
    try:
        c.execute('ALTER TABLE tickets ADD COLUMN warned INTEGER DEFAULT 0')
        conn.commit()
    except Exception:
        pass
    c.execute('DELETE FROM tickets')
    for ch_id, t in active_tickets.items():
        c.execute('''
            INSERT INTO tickets (
                channel_id, pihak1_id, pihak2_id, item_p1, item_p2,
                fee_final, fee_paid, link_server, admin_id, embed_message_id,
                ticket_number, opened_at, fee_warning_id, verified_by_id, warned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ch_id,
            t["pihak1"].id if t.get("pihak1") else None,
            t["pihak2"].id if t.get("pihak2") else None,
            t.get("item_p1"),
            t.get("item_p2"),
            t.get("fee_final"),
            1 if t.get("fee_paid") else 0,
            t.get("link_server"),
            t["admin"].id if t.get("admin") else None,
            t.get("embed_message_id"),
            t.get("ticket_number", 0),
            t["opened_at"].isoformat() if t.get("opened_at") else None,
            t.get("fee_warning_id"),
            t["verified_by"].id if t.get("verified_by") else None,
            1 if t.get("warned") else 0,
        ))
    conn.commit()
    conn.close()

async def load_tickets(guild, active_tickets):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM tickets')
    rows = c.fetchall()
    conn.close()
    for row in rows:
        try:
            p1 = await guild.fetch_member(row["pihak1_id"]) if row["pihak1_id"] else None
            p2 = await guild.fetch_member(row["pihak2_id"]) if row["pihak2_id"] else None
            adm = await guild.fetch_member(row["admin_id"]) if row["admin_id"] else None
            verified_by = await guild.fetch_member(row["verified_by_id"]) if row["verified_by_id"] else None
        except Exception as e:
            print(f"[WARNING] Gagal load tiket {row['channel_id']}: {e}")
            continue
        active_tickets[row["channel_id"]] = {
            "pihak1": p1,
            "pihak2": p2,
            "item_p1": row["item_p1"],
            "item_p2": row["item_p2"],
            "fee_final": row["fee_final"],
            "fee_paid": bool(row["fee_paid"]),
            "link_server": row["link_server"],
            "admin": adm,
            "embed_message_id": row["embed_message_id"],
            "ticket_number": row["ticket_number"],
            "opened_at": datetime.datetime.fromisoformat(row["opened_at"]) if row["opened_at"] else None,
            "fee_warning_id": row["fee_warning_id"],
            "verified_by": verified_by,
            "warned": bool(row["warned"]) if row["warned"] is not None else False,
        }
