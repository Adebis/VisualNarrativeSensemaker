SELECT * FROM (
	SELECT * FROM image_object_action_pairs
	INNER JOIN (
		SELECT * FROM doubly_linked_image_links
		WHERE greater_image_id IN (SELECT DISTINCT image_id FROM image_actions
			INNER JOIN(
				SELECT DISTINCT source_node_id as node_id FROM action_to_action_causal_links
				WHERE source_node_uri LIKE '%/eat%'
				UNION
				SELECT DISTINCT target_node_id as node_id FROM action_to_action_causal_links
				WHERE target_node_uri LIKE '%/eat%')
			ON image_actions.cs_node_id=node_id)
		AND lesser_image_id IN (SELECT DISTINCT image_id FROM image_actions
			INNER JOIN (
				SELECT DISTINCT source_node_id as linked_action_id FROM action_to_action_causal_links
				INNER JOIN (
					SELECT DISTINCT source_node_id as node_id FROM action_to_action_causal_links
					WHERE source_node_uri LIKE '%/eat%'
					UNION
					SELECT DISTINCT target_node_id as node_id FROM action_to_action_causal_links
					WHERE target_node_uri LIKE '%/eat%')
				ON action_to_action_causal_links.target_node_id = node_id
				UNION
				SELECT DISTINCT target_node_id as linked_action_id FROM action_to_action_causal_links
				INNER JOIN (
					SELECT DISTINCT source_node_id as node_id FROM action_to_action_causal_links
					WHERE source_node_uri LIKE '%/eat%'
					UNION
					SELECT DISTINCT target_node_id as node_id FROM action_to_action_causal_links
					WHERE target_node_uri LIKE '%/eat%')
				ON action_to_action_causal_links.source_node_id = node_id)
			ON image_actions.cs_node_id=linked_action_id)
		)
	ON image_object_action_pairs.image_id=greater_image_id 
)
WHERE action_cs_node_ids LIKE '%' || (
	SELECT DISTINCT source_node_id as node_id FROM action_to_action_causal_links
	WHERE source_node_uri LIKE '%/eat%'
	UNION
	SELECT DISTINCT target_node_id as node_id FROM action_to_action_causal_links
	WHERE target_node_uri LIKE '%/eat%') ||'%'