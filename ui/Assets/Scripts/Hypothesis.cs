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

public class ConceptEdgeEv : Evidence
{
    public int edge_id;
    public Edge edge;

    public ConceptEdgeEv(JToken token) : base(token)
    {
        this.edge_id = (int)token["edge"];
    }
}

public class OtherHypEv : Evidence
{
    public int hypothesis_id;
    public Hypothesis hypothesis;

    public OtherHypEv(JToken token) : base(token)
    {
        this.hypothesis_id = (int)token["hypothesis"];
    }
}

public class VisualSimEv : Evidence
{
    public int object_1_id;
    public ObjectNode object_1;
    public int object_2_id;
    public ObjectNode object_2;

    public VisualSimEv(JToken token) : base(token)
    {
        this.object_1_id = (int)token["object_1"];
        this.object_2_id = (int)token["object_2"];
    }
}

public class AttributeSimEv : Evidence
{
    public int object_1_id;
    public ObjectNode object_1;
    public int object_2_id;
    public ObjectNode object_2;

    public AttributeSimEv(JToken token) : base(token)
    {
        this.object_1_id = (int)token["object_1"];
        this.object_2_id = (int)token["object_2"];
    }
}

public class Hypothesis
{
    public int id;
    public string name;
    public List<int> premise_ids;
    public Dictionary<int, Hypothesis> premises;

    public Hypothesis(JToken token)
    {
        this.id = (int)token["id"];
        this.name = (string)token["name"];
        this.premise_ids = new List<int>();
        foreach (JToken premise_id in token["premises"])
        {
            this.premise_ids.Add((int)premise_id);
        }
        this.premises = new Dictionary<int, Hypothesis>();
    }
}

public class ConceptEdgeHyp : Hypothesis
{
    public int source_instance_id;
    public Node source_instance;
    public int target_instance_id;
    public Node target_instance;
    public int edge_id;
    public Edge edge;
    public ConceptEdgeEv concept_edge_ev;

    public ConceptEdgeHyp(JToken token) : base(token)
    {
        this.source_instance_id = (int)token["source_instance"];
        this.target_instance_id = (int)token["target_instance"];
        this.edge_id = (int)token["edge"];
        this.concept_edge_ev = new ConceptEdgeEv(token["concept_edge_ev"]);
    }
}

public class NewObjectHyp : Hypothesis
{
    public int object_id;
    public ObjectNode obj;
    public List<int> concept_edge_hyps_ids;
    public Dictionary<int, ConceptEdgeHyp> concept_edge_hyps;
    public Dictionary<int, OtherHypEv> concept_edge_hyp_ev;

    public NewObjectHyp(JToken token) : base(token)
    {
        this.object_id = (int)token["object"];
        this.concept_edge_hyps_ids = new List<int>();
        foreach (JToken concept_edge_hyp_id in token["concept_edge_hyps"])
        {
            this.concept_edge_hyps_ids.Add((int)concept_edge_hyp_id);
        }
        this.concept_edge_hyps = new Dictionary<int, ConceptEdgeHyp>();
        this.concept_edge_hyp_ev = new Dictionary<int, OtherHypEv>();
        foreach (JToken ce_hyp_ev_token in token["concept_edge_hyp_ev"])
        {
            var new_ev = new OtherHypEv(ce_hyp_ev_token);
            this.concept_edge_hyp_ev[new_ev.id] = new_ev;
        }
    }
}

public class SameObjectHyp : Hypothesis
{
    public int object_1_id;
    public ObjectNode object_1;
    public int object_2_id;
    public ObjectNode object_2;
    public Edge edge;
    public VisualSimEv visual_sim_ev;
    public AttributeSimEv attribute_sim_ev;
    public SameObjectHyp(JToken token) : base(token)
    {
        this.object_1_id = (int)token["object_1"];
        this.object_2_id = (int)token["object_2"];
        this.edge = new Edge(token["edge"]);
        this.visual_sim_ev = new VisualSimEv(token["visual_sim_ev"]);
        this.attribute_sim_ev = new AttributeSimEv(token["attribute_sim_ev"]);
    }
}

public class PersistObjectHyp : Hypothesis
{
    public int object_id;
    public ObjectNode object_;
    public int new_object_h_id;
    public NewObjectHyp new_object_hyp;
    public int same_object_h_id;
    public SameObjectHyp same_object_hyp;
    public OtherHypEv new_object_hyp_ev;
    public OtherHypEv same_object_hyp_ev;

    public PersistObjectHyp(JToken token) : base(token)
    {
        this.object_id = (int)token["object_"];
        this.new_object_h_id = (int)token["new_object_hyp"];
        this.same_object_h_id = (int)token["same_object_hyp"];
        this.new_object_hyp_ev = new OtherHypEv(token["new_object_hyp_ev"]);
        this.same_object_hyp_ev = new OtherHypEv(token["same_object_hyp_ev"]);
    }
}