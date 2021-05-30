class InvalidDAGError(Exception):
    """Error to indicate invalid DAG."""


def topsorted_layers(nodes, get_node_id_fn, get_parent_nodes, get_child_nodes):
    """Sorts the DAG of nodes in topological order.
    Args:
    nodes: A sequence of nodes.
    get_node_id_fn: Callable that returns a unique text identifier for a node.
    get_parent_nodes: Callable that returns a list of parent nodes for a node.
    get_child_nodes: Callable that returns a list of chlid nodes for a node.
    Returns:
    A list of topologically ordered node layers. Each layer of nodes is sorted
    by its node id given by `get_node_id_fn`.
    Raises:
    InvalidDAGError: If the input nodes don't form a DAG.
    ValueError: If the nodes are not unique.
    """
    # Make sure the nodes are unique.
    if len(set(get_node_id_fn(n) for n in nodes)) != len(nodes):
        raise ValueError('Nodes must have unique ids.')
    # The first layer contains nodes with no incoming edges.
    layer = [node for node in nodes if not get_parent_nodes(node)]

    visited = set()
    layers = []
    while layer:
        layer = sorted(layer, key=get_node_id_fn)
        layers.append(layer)

        next_layer = []
        for node in layer:
            visited.add(get_node_id_fn(node))
            for child_node in get_child_nodes(node):
                # Include the child node if all its parents are visited. If the child
                # node is part of a cycle, it will never be included since it will have
                # at least one unvisited parent node which is also part of the cycle.
                parent_node_ids = set(
                    get_node_id_fn(p) for p in get_parent_nodes(child_node))
                if parent_node_ids.issubset(visited):
                    next_layer.append(child_node)
        layer = next_layer

    # Nodes in cycles are not included in layers; raise an error if this happens.
    if sum(len(layer) for layer in layers) < len(nodes):
        raise InvalidDAGError('Cycle detected.')

    return layers
