from .bplustree import BPlusTree


class Table:
    """A database table backed by a B+ Tree index."""

    def __init__(self, name, order=4):
        self.name = name
        self.tree = BPlusTree(order=order)
        self.record_count = 0

    def insert(self, key, record: dict):
        existing = self.tree.search(key)
        self.tree.insert(key, record)
        if existing is None:
            self.record_count += 1

    def select(self, key):
        return self.tree.search(key)


    def update(self, key, new_record: dict):
        success = self.tree.update(key, new_record)
        if success:
            print(f"[{self.name}] Updated key={key} -> {new_record}")
        else:
            print(f"[{self.name}] Update failed: key={key} not found.")
        return success

    def delete(self, key):
        success = self.tree.delete(key)
        if success:
            self.record_count -= 1
            print(f"[{self.name}] Deleted key={key}.")
        else:
            print(f"[{self.name}] Delete failed: key={key} not found.")
        return success

    def range_query(self, start_key, end_key):
        return self.tree.range_query(start_key, end_key)

    def select_all(self):
        return self.tree.get_all()

    def count(self):
        return self.record_count

    def aggregate(self, field, operation="sum"):
        values = []
        for _, record in self.select_all():
            if isinstance(record, dict) and field in record:
                try:
                    values.append(float(record[field]))
                except (ValueError, TypeError):
                    pass
        if not values:
            return None
        ops = {
            "sum":   sum(values),
            "avg":   sum(values) / len(values),
            "min":   min(values),
            "max":   max(values),
            "count": len(values),
        }
        if operation not in ops:
            raise ValueError(f"Unknown operation: '{operation}'")
        return ops[operation]

    def visualize(self):
        return self.tree.visualize_tree()

    def __repr__(self):
        return f"<Table name='{self.name}' records={self.record_count}>"