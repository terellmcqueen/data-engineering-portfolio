"""
Flask app: 3 dashboards + LLM chat endpoint.
Each dashboard has its own data + context builder.
"""
import os
import json
import logging

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='static')

# pluggable LLM — mock locally, real SDK in production
try:
    import llm_sdk
    llm_generate = llm_sdk.generate
except ImportError:
    def llm_generate(prompt):
        return "[Mock] Deploy for real answers."

# load dashboard data at startup
_data = {}
for name in ('scheduling.json', 'forecast.json', 'delay.json'):
    path = os.path.join(app.static_folder or '.', name)
    try:
        with open(path) as f:
            _data[name.split('.')[0]] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass


@app.route('/health')
def health():
    return jsonify(status='ok')


@app.route('/api/ask', methods=['POST'])
def ask():
    body = request.get_json(force=True)
    question = body.get("question", "").strip()
    if not question:
        return jsonify(error='Missing question'), 400

    dashboard = body.get("dashboard", "scheduling")
    history = body.get("history", [])

    data = _data.get(dashboard)
    if not data:
        return jsonify(error=f"No data for {dashboard}"), 503

    context = build_context(dashboard, question, data)
    prompt = f"{SYSTEM_PROMPT}\n\n{context}\n\n"
    for msg in history:
        prompt += f"{msg['role'].title()}: {msg['content']}\n"
    prompt += f"User: {question}"

    try:
        return jsonify(answer=llm_generate(prompt))
    except Exception as e:
        return jsonify(error=str(e)), 500


def build_context(dashboard, question, data):
    """Select relevant data slice based on dashboard type."""
    if not data or len(data) < 2:
        return "No data available."

    cols, rows = data[0], data[1:]

    if dashboard == "forecast":
        # top 10 by forecast value, current week only
        fc_i = cols.index('facility') if 'facility' in cols else 0
        val_i = cols.index('forecast_p50') if 'forecast_p50' in cols else 1
        week_i = cols.index('weeks_from_now') if 'weeks_from_now' in cols else 2
        current = [r for r in rows if r[week_i] == 0]
        top10 = sorted(current, key=lambda r: r[val_i] or 0, reverse=True)[:10]
        lines = [f"{r[fc_i]}: {r[val_i]}" for r in top10]
        return f"Top 10 facilities (current week):\n" + "\n".join(lines)

    elif dashboard == "delay":
        fc_i = cols.index('facility') if 'facility' in cols else 0
        push_i = cols.index('push_delay') if 'push_delay' in cols else 1
        top10 = sorted(rows, key=lambda r: float(r[push_i] or 0), reverse=True)[:10]
        lines = [f"{r[fc_i]}: push={r[push_i]}" for r in top10]
        return f"Top 10 by push delay:\n" + "\n".join(lines)

    else:
        return f"Dataset: {len(rows)} rows, {len(cols)} columns"


SYSTEM_PROMPT = """You are an operations analyst assistant. Answer questions using ONLY the data provided in the context. If the data doesn't contain the answer, say so. Never invent numbers."""


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
