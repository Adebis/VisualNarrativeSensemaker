SELECT *
FROM image_actions
INNER JOIN (
	SELECT *
	FROM causal_links
	)
ON cs_node_id = source_node_id
WHERE image_id = 2359297
AND target_node_id IN (
	SELECT cs_node_id
	FROM image_actions
	INNER JOIN (
		SELECT *
		FROM causal_links
		)
	ON cs_node_id = target_node_id
	WHERE image_id = 2316406
	)
UNION
SELECT *
FROM image_actions
INNER JOIN (
	SELECT *
	FROM causal_links
	)
ON cs_node_id = source_node_id
WHERE image_id = 2316406
AND target_node_id IN (
	SELECT cs_node_id
	FROM image_actions
	INNER JOIN (
		SELECT *
		FROM causal_links
		)
	ON cs_node_id = target_node_id
	WHERE image_id = 2359297
	)