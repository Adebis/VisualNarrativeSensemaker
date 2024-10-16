WITH multi_linked_actions AS (
	SELECT DISTINCT source_action_label_id AS action_label_id 
	FROM multi_action_links
	UNION
	SELECT DISTINCT target_action_label_id AS action_label_id
	FROM multi_action_links
),
single_linked_actions AS (
	SELECT action_cs_nodes.action_label_id AS action_label_id FROM action_to_action_causal_links
	INNER JOIN action_cs_nodes
	ON action_cs_nodes.cs_node_id = action_to_action_causal_links.source_node_id
	UNION
	SELECT action_cs_nodes.action_label_id AS action_label_id FROM action_to_action_causal_links
	INNER JOIN action_cs_nodes
	ON action_cs_nodes.cs_node_id = action_to_action_causal_links.target_node_id
)

SELECT DISTINCT image_id
FROM image_object_action_pairs
INNER JOIN multi_linked_actions
ON multi_linked_actions.action_label_id = image_object_action_pairs.action_label_id
