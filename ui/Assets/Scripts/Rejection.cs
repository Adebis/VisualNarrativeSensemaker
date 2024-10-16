using Newtonsoft.Json.Linq;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEditor.UI;

public class Rejection
{
    private RejectionImport imported_data;

    public Hypothesis rejected_hyp;
    public string explanation;

    public Rejection(RejectionImport imported_data)
    {
        this.imported_data = imported_data;

        this.explanation = imported_data.explanation;
    }

    public void PopulateHypotheses(Dictionary<int, Hypothesis> all_hypotheses)
    {
        this.rejected_hyp = all_hypotheses[this.imported_data.rejected_hyp_id];
    }

    public RejectionImport ImportedData
    {
        get { return this.imported_data; }
    }
}

public class HypConRejection : Rejection
{
    public Hypothesis contradicting_hyp;
    public Contradiction contradiction;

    public HypConRejection(HypConRejectionImport imported_data) : base(imported_data)
    {

    }

    public new void PopulateHypotheses(Dictionary<int, Hypothesis> all_hypotheses)
    {
        base.PopulateHypotheses(all_hypotheses);
        this.contradicting_hyp = all_hypotheses[this.ImportedData.contradicting_hyp_id];
    }

    public void PopulateContradictions(List<Contradiction> all_contradictions)
    {
        foreach (Contradiction contradiction in all_contradictions)
        {
            if (contradiction.id == this.ImportedData.contradiction_id)
            {
                this.contradiction = contradiction;
                break;
            }
        }
    }

    // Properties
    public new HypConRejectionImport ImportedData
    {
        get { return (HypConRejectionImport)base.ImportedData; }
    }
}

public class HypSetConRejection : Rejection
{
    public HypothesisSet contradicting_hyp_set;
    public Contradiction contradiction;

    public HypSetConRejection(HypSetConRejectionImport imported_data) : base(imported_data)
    {

    }

    public new void PopulateHypotheses(Dictionary<int, Hypothesis> all_hypotheses)
    {
        base.PopulateHypotheses(all_hypotheses);
    }

    public void PopulateHypothesisSets(Dictionary<int, HypothesisSet> all_hyp_sets)
    {
        this.contradicting_hyp_set = all_hyp_sets[this.ImportedData.contradicting_hyp_set_id];
    }

    public void PopulateContradictions(List<Contradiction> all_contradictions)
    {
        foreach (Contradiction contradiction in all_contradictions)
        {
            if (contradiction.id == this.ImportedData.contradiction_id)
            {
                this.contradiction = contradiction;
                break;
            }
        }
    }

    // Properties
    public new HypSetConRejectionImport ImportedData
    {
        get { return (HypSetConRejectionImport)base.ImportedData; }
    }
}

public class CausalCycleRejection : Rejection
{
    public List<Hypothesis> contradicting_hyps;
    public CausalCycleCon contradiction;

    public CausalCycleRejection(CausalCycleRejectionImport imported_data) : base(imported_data)
    {
        this.contradicting_hyps = new List<Hypothesis>();
    }

    public new void PopulateHypotheses(Dictionary<int, Hypothesis> all_hypotheses)
    {
        base.PopulateHypotheses(all_hypotheses);
        foreach (int hyp_id in this.ImportedData.contradicting_hyp_ids)
        {
            this.contradicting_hyps.Append(all_hypotheses[hyp_id]);
        }
    }

    public void PopulateContradictions(List<Contradiction> all_contradictions)
    {
        foreach (Contradiction contradiction in all_contradictions)
        {
            if (contradiction.id == this.ImportedData.contradiction_id)
            {
                try
                {
                    this.contradiction = (CausalCycleCon)contradiction;
                }
                catch (Exception e)
                {
                    Console.WriteLine($"Rejections.CausalCycleRejection.PopulateContradictions: Error! {e}");
                }
                break;
            }
        }
    }

    // Properties
    public new CausalCycleRejectionImport ImportedData
    {
        get { return (CausalCycleRejectionImport)base.ImportedData; }
    }
}