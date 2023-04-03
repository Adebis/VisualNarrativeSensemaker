using Newtonsoft.Json.Linq;

using System.Collections;
using System.Collections.Generic;

public class Evidence
{
    public int id;
    public float score;

    public Evidence(JToken token)
    {
        this.id = (int)token["id"];
        this.score = (float)token["score"];
    }
}

public class ConceptEdgeEvidence : Evidence
{
    public int edge_id;
    public Edge edge;

    public ConceptEdgeEvidence(JToken token) : base(token)
    {
        this.edge_id = (int)token["edge"];
    }
}

public class OtherHypothesisEvidence : Evidence
{
    public int hypothesis_id;
    public Hypothesis hypothesis;

    public OtherHypothesisEvidence(JToken token) : base(token)
    {
        this.hypothesis_id = (int)token["hypothesis"];
    }
}

public class VisualSimilarityEvidence : Evidence
{
    public int object_1_id;
    public ObjectNode object_1;
    public int object_2_id;
    public ObjectNode object_2;

    public VisualSimilarityEvidence(JToken token) : base(token)
    {
        this.object_1_id = (int)token["object_1"];
        this.object_2_id = (int)token["object_2"];
    }
}

public class AttributeSimilarityEvidence : Evidence
{
    public int object_1_id;
    public ObjectNode object_1;
    public int object_2_id;
    public ObjectNode object_2;

    public AttributeSimilarityEvidence(JToken token) : base(token)
    {
        this.object_1_id = (int)token["object_1"];
        this.object_2_id = (int)token["object_2"];
    }
}

public class Hypothesis
{
    public int id;
    public string name;
    public float score;
    public List<Evidence> evidence;
    public List<int> premise_ids;
    public Dictionary<int, Hypothesis> premises;

    public Hypothesis(JToken token)
    {
        this.id = (int)token["id"];
        this.name = (string)token["name"];
        this.score = (float)token["score"];
        this.evidence = new List<Evidence>();
        foreach (JToken evidence_token in token["evidence"])
        {
            this.evidence.Add(new Evidence(evidence_token));
        }
        this.premise_ids = new List<int>();
        foreach (JToken premise_id in token["premises"])
        {
            this.premise_ids.Add((int)premise_id);
        }
        this.premises = new Dictionary<int, Hypothesis>();
    }
}

public class ConceptEdgeHypothesis : Hypothesis
{
    public int source_instance_id;
    public Node source_instance;
    public int target_instance_id;
    public Node target_instance;
    public int edge_id;
    public Edge edge;

    public ConceptEdgeHypothesis(JToken token) : base(token)
    {
        this.source_instance_id = (int)token["source_instance"];
        this.target_instance_id = (int)token["target_instance"];
        this.edge_id = (int)token["edge"];
    }
}

public class OffscreenObjectHypothesis : Hypothesis
{
    public int object_id;
    public ObjectNode obj;
    public List<int> concept_edge_hypothesis_ids;
    public Dictionary<int, ConceptEdgeHypothesis> concept_edge_hypotheses;


    public OffscreenObjectHypothesis(JToken token) : base(token)
    {
        this.object_id = (int)token["object"];
        this.concept_edge_hypothesis_ids = new List<int>();
        foreach (JToken ce_hypothesis_id in token["concept_edge_hypotheses"])
        {
            this.concept_edge_hypothesis_ids.Add((int)ce_hypothesis_id);
        }
        this.concept_edge_hypotheses = new Dictionary<int, ConceptEdgeHypothesis>();
    }
}

public class ObjectDuplicateHypothesis : Hypothesis
{
    public int object_1_id;
    public ObjectNode object_1;
    public int object_2_id;
    public ObjectNode object_2;

    public Edge edge;

    public ObjectDuplicateHypothesis(JToken token) : base(token)
    {
        this.object_1_id = (int)token["object_1"];
        this.object_2_id = (int)token["object_2"];
        this.edge = new Edge(token["edge"]);
    }
}

public class ObjectPersistenceHypothesis : Hypothesis
{
    public int object_id;
    public ObjectNode object_;
    public int offscreen_obj_h_id;
    public OffscreenObjectHypothesis offscreen_object_hypothesis;
    public int object_duplicate_h_id;
    public ObjectDuplicateHypothesis object_duplicate_hypothesis;

    public ObjectPersistenceHypothesis(JToken token) : base(token)
    {
        this.object_id = (int)token["object_"];
        this.offscreen_obj_h_id = (int)token["offscreen_object_hypothesis"];
        this.object_duplicate_h_id = (int)token["object_duplicate_hypothesis"];
    }
}