using Newtonsoft.Json.Linq;
using System;
using System.Collections;
using System.Collections.Generic;

public class Contradiction
{
	private ContradictionImport imported_data;

    public int id;
	public string explanation;

	public Contradiction(ContradictionImport imported_data)
	{
		this.imported_data = imported_data;

		this.id = imported_data.id;
		this.explanation = imported_data.explanation;
    }

	public virtual bool HasHypothesis(Hypothesis hyp)
	{
		return false;
	}

	// Properties
	public ContradictionImport ImportedData
	{ 
		get { return this.imported_data; } 
	}
}

public class HypothesisCon : Contradiction
{
	public Hypothesis hypothesis_1;
	public Hypothesis hypothesis_2;

	public HypothesisCon(HypothesisConImport imported_data) : base(imported_data)
	{

	}

	public void PopulateHypotheses(Dictionary<int, Hypothesis> all_hypotheses)
	{
		this.hypothesis_1 = all_hypotheses[this.ImportedData.hypothesis_1_id];
		this.hypothesis_2 = all_hypotheses[this.ImportedData.hypothesis_2_id];
	}

	public override bool HasHypothesis(Hypothesis hyp)
	{
		if (this.hypothesis_1 == hyp)
			return true;
		else if (this.hypothesis_2 == hyp)
			return true;
		else
			return false;
	}

	public Hypothesis GetOtherHypothesis(Hypothesis hyp)
	{
		if (this.hypothesis_1 == hyp)
			return this.hypothesis_2;
		else if (this.hypothesis_2 == hyp)
			return this.hypothesis_1;
		else
			return null;
	}

	// Properties
	public new HypothesisConImport ImportedData
	{
		get { return (HypothesisConImport)base.ImportedData; }
	}
}

public class InImageTransCon : HypothesisCon
{
	public ObjectNode obj_1;
	public ObjectNode obj_2;
	public ObjectNode shared_obj;

	public InImageTransCon(InImageTransConImport imported_data) : base(imported_data)
	{

    }

	public void PopulateNodes(Dictionary<int, Node> all_nodes)
	{
		this.obj_1 = (ObjectNode)all_nodes[this.ImportedData.obj_1_id];
        this.obj_2 = (ObjectNode)all_nodes[this.ImportedData.obj_2_id];
        this.shared_obj = (ObjectNode)all_nodes[this.ImportedData.shared_obj_id];
    }

    public override string ToString()
    {
		string to_string = "InImageTransCon between Hypotheses " + this.ImportedData.hypothesis_1_id.ToString() + " and "
			+ this.ImportedData.hypothesis_2_id.ToString() + ". obj_1: " + this.obj_1.name + ", obj_2: " + this.obj_2.name + ", "
			+ "shared_obj: " + this.shared_obj.name;
		return to_string;
    }

	// Properties
	public new InImageTransConImport ImportedData
	{
		get { return (InImageTransConImport)base.ImportedData; }
	}
}

public class TweenImageTransCon : HypothesisCon
{
    public ObjectNode obj_1;
    public ObjectNode obj_2;
    public ObjectNode shared_obj;
	public Hypothesis joining_hyp;
	public int hyp_set_id;

    public TweenImageTransCon(TweenImageTransConImport imported_data) : base(imported_data)
    {
		this.hyp_set_id = imported_data.hyp_set_id;
    }

	public void PopulateNodes(Dictionary<int, Node> all_nodes)
	{
		this.obj_1 = (ObjectNode)all_nodes[this.ImportedData.obj_1_id];
        this.obj_2 = (ObjectNode)all_nodes[this.ImportedData.obj_2_id];
        this.shared_obj = (ObjectNode)all_nodes[this.ImportedData.shared_obj_id];
    }

	public new void PopulateHypotheses(Dictionary<int, Hypothesis> all_hypotheses)
	{
		base.PopulateHypotheses(all_hypotheses);
		this.joining_hyp = all_hypotheses[this.ImportedData.joining_hyp_id];
	}

	public override bool HasHypothesis(Hypothesis hypothesis)
	{
        if (base.HasHypothesis(hypothesis))
        {
			return true;
        }
		/*
		else if (this.joining_hyp == hypothesis)
		{
			return true;
		}
		*/
		else
		{
			return false;
		}
    }

    // Whether or not the contradiction is active for a given solution set. 
    public bool IsActive(Solution solution)
	{
		// Check to see if the joining hypothesis is not in the solution's set of accepted
		// hypotheses.
		// If so, this contradiction is active.
		if (!solution.ImportedData.accepted_hypothesis_ids.Contains(this.joining_hyp.id))
		{
			return true;
		}
		else
		{
			return false;
		}
    }

    public override string ToString()
    {
		string to_string = "TweenImageTransCon between Hypotheses " + this.ImportedData.hypothesis_1_id.ToString() + " and "
			+ this.ImportedData.hypothesis_2_id.ToString() + ". obj_1: " + this.obj_1.name + ", obj_2: " + this.obj_2.name + ", "
            + "shared_obj: " + this.shared_obj.name + ", joining hyp: " + this.joining_hyp.ToString();

        return to_string;
    }

	// Properties
	public new TweenImageTransConImport ImportedData
	{
		get { return (TweenImageTransConImport)base.ImportedData; }
	}
}

public class CausalHypFlowCon : HypothesisCon
{
	public ImageData image_1;
	public ImageData image_2;

    public CausalHypFlowCon(CausalHypFlowConImport imported_data) : base(imported_data)
    {

    }

    public void PopulateImages(Dictionary<int, ImageData> all_images)
    {
        this.image_1 = all_images[this.ImportedData.image_1_id];
        this.image_2 = all_images[this.ImportedData.image_2_id];
    }

    // Properties
    public new CausalHypFlowConImport ImportedData
    {
        get { return (CausalHypFlowConImport)base.ImportedData; }
    }
}

public class HypothesisSetCon : Contradiction
{
	public HypothesisSet hyp_set_1;
	public HypothesisSet hyp_set_2;

    public HypothesisSetCon(HypothesisSetConImport imported_data) : base(imported_data)
	{

	}

	public void PopulateHypothesisSets(Dictionary<int, HypothesisSet> all_hyp_sets)
	{
		this.hyp_set_1 = all_hyp_sets[this.ImportedData.hyp_set_1_id];
        this.hyp_set_2 = all_hyp_sets[this.ImportedData.hyp_set_2_id];
    }

	public override bool HasHypothesis(Hypothesis hyp)
	{
		if (hyp_set_1.HasHypothesis(hyp) || hyp_set_2.HasHypothesis(hyp))
			return true;
		else
			return false;
	}

	// Properties
	public new HypothesisSetConImport ImportedData
	{
		get { return (HypothesisSetConImport)base.ImportedData; }
	}
}

public class CausalChainFlowCon : HypothesisSetCon
{
	public ImageData image_1;
	public ImageData image_2;

	public CausalChainFlowCon(CausalChainFlowConImport imported_data) : base(imported_data)
	{

	}

	public void PopulateImages(Dictionary<int, ImageData> all_images)
	{
		this.image_1 = all_images[this.ImportedData.image_1_id];
        this.image_2 = all_images[this.ImportedData.image_2_id];
    }

    // Properties
    public new CausalChainFlowConImport ImportedData
    {
        get { return (CausalChainFlowConImport)base.ImportedData; }
    }
}

public class CausalCycleCon : Contradiction
{
	public ImageData image;
	public CausalHypChain causal_chain;
	public List<HypothesisSet> subsets;

	public CausalCycleCon(CausalCycleConImport imported_data) : base(imported_data)
	{
		this.subsets = new List<HypothesisSet>();

    }

    public void PopulateImages(Dictionary<int, ImageData> all_images)
    {
        this.image = all_images[this.ImportedData.image_id];
    }

	public void PopulateHypothesisSets(Dictionary<int, HypothesisSet> all_hyp_sets)
	{
		this.causal_chain = (CausalHypChain)all_hyp_sets[this.ImportedData.causal_chain_id];
		foreach (int subset_id in this.ImportedData.subset_ids)
		{
			this.subsets.Add(all_hyp_sets[subset_id]);
		}
	}

    // Properties
    public new CausalCycleConImport ImportedData
    {
        get { return (CausalCycleConImport)base.ImportedData; }
    }
}