import cloudpickle

obj = {"a": 1, "fn": lambda x: x + 1}
data = cloudpickle.dumps(obj)
back = cloudpickle.loads(data)
assert back["a"] == 1
assert back["fn"](41) == 42

print("cloudpickle test package: OK")