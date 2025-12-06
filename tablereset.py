# import sqlite3

# DB_PATH = "sales_eva.db"  # change path if DB is somewhere else

# conn = sqlite3.connect(DB_PATH)
# cur = conn.cursor()

# try:
#     print("Renaming key_benefit → benefit ...")
#     cur.execute("ALTER TABLE case_studies RENAME COLUMN key_benefit TO benefit;")
#     print("DONE")
# except Exception as e:
#     print("Already renamed or error:", e)

# try:
#     print("Renaming file_link → link ...")
#     cur.execute("ALTER TABLE case_studies RENAME COLUMN file_link TO link;")
#     print("DONE")
# except Exception as e:
#     print("Already renamed or error:", e)

# conn.commit()
# conn.close()

# print("\n🎯 Table update complete!")

import sqlite3

DB_PATH = "./sales_eva.db"  # update if your DB file location is different

def create_feedback_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opportunity_id INTEGER,
        offering_id INTEGER,
        rating INTEGER,
        comments TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print("✔ feedback table created successfully!")

if __name__ == "__main__":
    create_feedback_table()
