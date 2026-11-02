# Start with an authorized agent

**English** | [한국어](agent-kit.ko.md)

Use this kit to give an agent a bounded local knowledge task. The CLI stores prepared
text and sources; the agent supplies reading, synthesis and judgment. Install with the
[README quickstart](../README.md#quick-start), then choose one entry:

- [Durable workflow](../workflows/AGENT-WORKFLOW.md): command sequence, access/privacy,
  data versus instructions, retry/CAS, declarations and incomplete results. This is the
  authoritative operational guide; exact option/schema rules live in the reference.
- [Copyable task prompt](../templates/task-workflow.md): fill goal, allowed paths, stable
  task ID and saved request/revision records, then give it to your chosen agent.
- [Body template](../templates/concept-body.md): prepare searchable Markdown outside
  the bundle. Recall does not search annotation fields.

No host integration, model, account or Obsidian is required by the CLI. The kit does not
install hooks or global rules. Real host/model integration is not proved by a deterministic
CLI example. Local storage makes no runtime uploads; an external agent may send allowed
inputs to its provider under its own policy. Authorize access and transfers explicitly.

For the broader preserve/curate/connect/reuse/revise experience and its quality criteria,
read [the knowledge-practice specification](knowledge-practice.md). It separates product
requirements from today's CLI mechanics and the later fresh-agent pilot.

For natural save/connect/revise/reuse requests, start at [the knowledge kit](../knowledge-kit/START.md).
It includes a safe local profile, meaning-centered workflow and human navigation templates;
profiles are read by your authorized agent, not a new CLI loader.

## Run the synthetic reuse demo

With the project environment active, choose a new or empty output directory:

```sh
python examples/knowledge_reuse.py --output /tmp/my-new-second-brain-demo
```

The demo reads only named synthetic fixtures and writes its own bundle/prepared/results.
It refuses a nonempty target, file or output symlink. A failure can leave partial artifacts;
it does not delete or overwrite earlier output. It saves a sourced note, records a process
review, reuses current knowledge for a later checklist, then revises and reuses it again.

Inspect summary.json and transcript.json, reuse-before.json/reuse-after.json, and wiki/
for exact revisions and source bytes. Reuse is a deterministic copy, not LLM reasoning or
fact checking. The later content change resets inherited review status. Follow the workflow
for your own authorized task rather than treating a demo actor label as authenticated trust.
