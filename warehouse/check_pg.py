import psycopg2

passwords = ['', 'postgres', 'admin', 'root', 'password', '1234', '123456', 'finsight_secure_pass_2026', 'nagesh', 'Nagesh', 'Nagesh@123']
success = False
for pwd in passwords:
    try:
        conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password=pwd, connect_timeout=2)
        print(f"[+] SUCCESS! Connected to PostgreSQL with password: '{pwd}'")
        conn.close()
        success = True
        break
    except Exception as e:
        err = str(e).strip().splitlines()[0]
        print(f"[-] Tried '{pwd}': {err}")

if not success:
    print("\n[!] Could not connect with standard test passwords. Will check user account or prompt.")
