import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import pymysql

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "banco_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sua_senha_forte_aqui")
DB_NAME = os.getenv("DB_NAME", "banco_simples")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))

LIMIT_PER_WITHDRAW = Decimal("500.00")
MAX_WITHDRAWS_PER_DAY = 3

app = Flask(__name__)
CORS(app)


def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def init_db():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS operations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                type ENUM('deposit','withdraw') NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)


def parse_amount(raw: str) -> Decimal:
    if raw is None:
        raise InvalidOperation("Empty amount")
    raw = raw.strip().replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "")
    raw = raw.replace(",", ".")
    d = Decimal(raw)
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def current_balance(conn) -> Decimal:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(CASE WHEN type='deposit' THEN amount ELSE -amount END), 0) AS saldo
            FROM operations
        """)
        row = cur.fetchone()
        return Decimal(row["saldo"]).quantize(Decimal("0.01"))


def todays_withdraw_count(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS c FROM operations
            WHERE type='withdraw' AND DATE(created_at) = CURDATE()
        """)
        row = cur.fetchone()
        return int(row["c"])


def insert_operation(conn, op_type: str, amount: Decimal):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO operations (type, amount) VALUES (%s, %s)",
            (op_type, str(amount)),
        )


def get_operations(conn, limit: int = 100):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, type, amount, created_at
            FROM operations
            ORDER BY created_at DESC, id DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/extract")
def api_extract():
    with get_conn() as conn:
        saldo = current_balance(conn)
        ops = get_operations(conn, limit=200)
        return jsonify({
            "balance": float(saldo),
            "operations": [
                {
                    "id": o["id"],
                    "type": o["type"],
                    "amount": float(o["amount"]),
                    "created_at": o["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                } for o in ops
            ]
        }), 200


@app.post("/api/deposit")
def api_deposit():
    data = request.get_json(silent=True) or {}
    raw_amount = data.get("amount") or data.get("valor") or ""
    try:
        amount = parse_amount(str(raw_amount))
    except Exception:
        return jsonify({"error": "Valor inválido."}), 400
    if amount <= 0:
        return jsonify({"error": "O valor deve ser maior que zero."}), 400

    with get_conn() as conn:
        insert_operation(conn, "deposit", amount)
        saldo = current_balance(conn)
        return jsonify({
            "message": "Depósito realizado com sucesso.",
            "balance": float(saldo)
        }), 201


@app.post("/api/withdraw")
def api_withdraw():
    data = request.get_json(silent=True) or {}
    raw_amount = data.get("amount") or data.get("valor") or ""
    try:
        amount = parse_amount(str(raw_amount))
    except Exception:
        return jsonify({"error": "Valor inválido."}), 400
    if amount <= 0:
        return jsonify({"error": "O valor deve ser maior que zero."}), 400

    with get_conn() as conn:
        saldo = current_balance(conn)
        if amount > saldo:
            return jsonify({"error": "Operação falhou! Saldo insuficiente."}), 400

        if amount > LIMIT_PER_WITHDRAW:
            return jsonify({"error": f"Operação falhou! Limite por saque é {LIMIT_PER_WITHDRAW}."}), 400

        saques_hoje = todays_withdraw_count(conn)
        if saques_hoje >= MAX_WITHDRAWS_PER_DAY:
            return jsonify({"error": "Operação falhou! Limite diário de saques excedido (3)."}), 400

        insert_operation(conn, "withdraw", amount)
        novo_saldo = current_balance(conn)
        return jsonify({
            "message": "Saque realizado com sucesso.",
            "balance": float(novo_saldo),
            "withdraws_today": saques_hoje + 1
        }), 201


@app.post("/api/reset")
def api_reset():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE operations")
    return jsonify({"message": "Sistema reiniciado (tabela limpa)."}), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=True)
