import math
import graphviz


class BPlusTreeNode:
    def __init__(self, leaf=False):
        self.leaf = leaf
        self.keys = []
        self.values = []
        self.children = []
        self.next = None


class BPlusTree:
    def __init__(self, order=4):
        self.root = BPlusTreeNode(leaf=True)
        self.order = order
        self.min_keys = math.ceil(order / 2) - 1

    # SEARCH 
    def search(self, key):
        node = self.root
        while not node.leaf:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            node = node.children[i]
        for i, k in enumerate(node.keys):
            if k == key:
                return node.values[i]
        return None

    # RANGE QUERY
    def range_query(self, start_key, end_key):
        results = []
        node = self.root
        while not node.leaf:
            i = 0
            while i < len(node.keys) and start_key >= node.keys[i]:
                i += 1
            node = node.children[i]
        while node is not None:
            for i, k in enumerate(node.keys):
                if start_key <= k <= end_key:
                    results.append((k, node.values[i]))
                elif k > end_key:
                    return results
            node = node.next
        return results

    # GET ALL
    def get_all(self):
        results = []
        node = self.root
        while not node.leaf:
            node = node.children[0]
        while node is not None:
            for i in range(len(node.keys)):
                results.append((node.keys[i], node.values[i]))
            node = node.next
        return results

    # INSERT 
    def insert(self, key, value):
        root = self.root
        if len(root.keys) == self.order - 1:
            new_root = BPlusTreeNode(leaf=False)
            self.root = new_root
            new_root.children.append(root)
            self._split_child(new_root, 0)
            self._insert_non_full(new_root, key, value)
        else:
            self._insert_non_full(root, key, value)

    def _insert_non_full(self, node, key, value):
        if node.leaf:
            i = 0
            while i < len(node.keys) and key > node.keys[i]:
                i += 1
            if i < len(node.keys) and node.keys[i] == key:
                node.values[i] = value
            else:
                node.keys.insert(i, key)
                node.values.insert(i, value)
        else:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            if len(node.children[i].keys) == self.order - 1:
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            self._insert_non_full(node.children[i], key, value)

    def _split_child(self, parent, index):
        child = parent.children[index]
        new_node = BPlusTreeNode(leaf=child.leaf)
        mid = len(child.keys) // 2
        if child.leaf:
            new_node.keys   = child.keys[mid:]
            new_node.values = child.values[mid:]
            child.keys      = child.keys[:mid]
            child.values    = child.values[:mid]
            parent.keys.insert(index, new_node.keys[0])
            parent.children.insert(index + 1, new_node)
            new_node.next = child.next
            child.next    = new_node
        else:
            promoted_key       = child.keys[mid]
            new_node.keys      = child.keys[mid + 1:]
            new_node.children  = child.children[mid + 1:]
            child.keys         = child.keys[:mid]
            child.children     = child.children[:mid + 1]
            parent.keys.insert(index, promoted_key)
            parent.children.insert(index + 1, new_node)

    # DELETE
    def delete(self, key):
        if not self.root:
            return False
        result = self._delete(self.root, key)
        if not self.root.leaf and len(self.root.keys) == 0:
            self.root = self.root.children[0]
        return result

    def _delete(self, node, key):
        if node.leaf:
            for i, k in enumerate(node.keys):
                if k == key:
                    node.keys.pop(i)
                    node.values.pop(i)
                    return True
            return False
        i = 0
        while i < len(node.keys) and key >= node.keys[i]:
            i += 1
        child = node.children[i]
        if len(child.keys) <= self.min_keys:
            self._fill_child(node, i)
            if i > len(node.keys):
                i -= 1
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
        return self._delete(node.children[i], key)

    def _fill_child(self, node, index):
        if index > 0 and len(node.children[index - 1].keys) > self.min_keys:
            self._borrow_from_prev(node, index)
        elif index < len(node.children) - 1 and len(node.children[index + 1].keys) > self.min_keys:
            self._borrow_from_next(node, index)
        else:
            if index < len(node.children) - 1:
                self._merge(node, index)
            else:
                self._merge(node, index - 1)

    def _borrow_from_prev(self, node, index):
        child = node.children[index]
        left  = node.children[index - 1]
        if child.leaf:
            child.keys.insert(0, left.keys.pop(-1))
            child.values.insert(0, left.values.pop(-1))
            node.keys[index - 1] = child.keys[0]
        else:
            child.keys.insert(0, node.keys[index - 1])
            node.keys[index - 1] = left.keys.pop(-1)
            child.children.insert(0, left.children.pop(-1))

    def _borrow_from_next(self, node, index):
        child = node.children[index]
        right = node.children[index + 1]
        if child.leaf:
            child.keys.append(right.keys.pop(0))
            child.values.append(right.values.pop(0))
            node.keys[index] = right.keys[0]
        else:
            child.keys.append(node.keys[index])
            node.keys[index] = right.keys.pop(0)
            child.children.append(right.children.pop(0))

    def _merge(self, node, index):
        left  = node.children[index]
        right = node.children[index + 1]
        if left.leaf:
            left.keys   += right.keys
            left.values += right.values
            left.next    = right.next
        else:
            left.keys.append(node.keys[index])
            left.keys      += right.keys
            left.children  += right.children
        node.keys.pop(index)
        node.children.pop(index + 1)

    # UPDATE 
    def update(self, key, new_value):
        node = self.root
        while not node.leaf:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            node = node.children[i]
        for i, k in enumerate(node.keys):
            if k == key:
                node.values[i] = new_value
                return True
        return False

    # VISUALIZE 
    @staticmethod
    def _label(node):
        """Build a Graphviz HTML-like label for a node."""
        if node.leaf:
            cells = "".join(
                "<TD BORDER='1' BGCOLOR='#fffacd' CELLPADDING='4'>"
                "<B>{k}</B><BR/>"
                "<FONT POINT-SIZE='8'>{v}</FONT>"
                "</TD>".format(
                    k=str(key).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                    v=str(val)[:10].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                )
                for key, val in zip(node.keys, node.values)
            )
        else:
            cells = "".join(
                "<TD BORDER='1' BGCOLOR='#cce5ff' CELLPADDING='5'>"
                "<B>{k}</B>"
                "</TD>".format(
                    k=str(key).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                )
                for key in node.keys
            )
        return "<<TABLE BORDER='0' CELLBORDER='0' CELLSPACING='2'><TR>{}</TR></TABLE>>".format(cells)

    def visualize_tree(self):
        """
        Returns a graphviz.Digraph representing the B+ Tree.
        Internal nodes are blue, leaf nodes are yellow.
        Leaf linked-list connections shown via invisible ordering edges
        inside a same-rank subgraph (avoids the 'flat edge' engine error).
        """
        dot = graphviz.Digraph(comment="B+ Tree")
        dot.attr(rankdir="TB", ranksep="0.5", nodesep="0.3")
        dot.attr("node", shape="none", margin="0")

        def add_nodes(node):
            dot.node(str(id(node)), self._label(node))
            if not node.leaf:
                for child in node.children:
                    add_nodes(child)

        def add_edges(node):
            if not node.leaf:
                for child in node.children:
                    dot.edge(str(id(node)), str(id(child)))
                    add_edges(child)

        add_nodes(self.root)
        add_edges(self.root)

        # Collect leaves in linked-list order
        leaves = []
        cur = self.root
        while not cur.leaf:
            cur = cur.children[0]
        while cur:
            leaves.append(cur)
            cur = cur.next

        # Force leaves onto the same rank; use invisible edges for left-to-right order
        if len(leaves) > 1:
            with dot.subgraph() as s:
                s.attr(rank="same")
                for lf in leaves:
                    s.node(str(id(lf)))
                # Invisible edges preserve order without triggering engine error
                for i in range(len(leaves) - 1):
                    s.edge(
                        str(id(leaves[i])),
                        str(id(leaves[i + 1])),
                        style="invis"
                    )

        return dot