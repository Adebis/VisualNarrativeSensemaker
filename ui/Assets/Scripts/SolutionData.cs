using Newtonsoft.Json.Linq;

using System.Collections;
using System.Collections.Generic;

public struct ParameterSet
{
    public int id;
    public string name;
    public float no_relationship_penalty;
    public float relationship_score_minimum;
    public float relationship_score_weight;
    public float continuity_penalty;

    public ParameterSet(JToken token)
    {
        this.id = (int)token["id"];
        this.name = (string)token["name"];
        this.no_relationship_penalty = (float)token["no_relationship_penalty"];
        this.relationship_score_minimum = (float)token["relationship_score_minimum"];
        this.relationship_score_weight = (float)token["relationship_score_weight"];
        this.continuity_penalty = (float)token["continuity_penalty"];
    }
}

public class Solution
{
    public int id;
    public int parameters_id;
    public ParameterSet parameters;
    public List<int> accepted_hypothesis_ids;
    public Dictionary<int, Hypothesis> accepted_hypotheses;

    public Solution(JToken token)
    {
        this.id = (int)token["id"];
        this.parameters_id = (int)token["parameters"];
        this.accepted_hypothesis_ids = new List<int>();
        foreach (JToken h_id in token["accepted_hypotheses"])
        {
            this.accepted_hypothesis_ids.Add((int)h_id);
        }
        this.accepted_hypotheses = new Dictionary<int, Hypothesis>();
    }
}