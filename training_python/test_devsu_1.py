import json

class Product:
    def __init__(self, product_id, name):
        self.product_id = product_id
        self.name = name

    def __str__(self):
        return f"Product {self.product_id}: {self.name}"

class ValueErrorProduct(ValueError):
    pass

def check_product_definition(json_product):
    try:
        data = json.loads(json_product)
    except json.JSONDecodeError:
        raise ValueErrorProduct("Invalid json string")

    if "id" not in data:
        raise ValueErrorProduct("Missing id field")
    if not isinstance(data["id"], int):
        raise ValueErrorProduct("The id field must be an integer")

    if "name" not in data:
        raise ValueErrorProduct("Missing name field")
    if not isinstance(data["name"], str):
        raise ValueErrorProduct("The name field must be a string")

    return Product(data["id"], data["name"])