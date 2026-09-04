from flask import jsonify


def success(data, status=200, meta=None):
    return jsonify({"meta": meta or {}, "data": data}), status


def error(message, status):
    return jsonify({"meta": {}, "data": None, "error": {"message": message}}), status
