# Architecture Diagram (PDF-Ready Description)

Use this as a diagram spec in your PDF tool (draw.io, Figma, PowerPoint, or Mermaid).

Title: The Brownfield Cartographer Pipeline

Nodes:
1. Input Repo (GitHub URL or local path)
2. Surveyor
3. Hydrologist
4. Semanticist
5. Archivist
6. KnowledgeGraph (shared state)
7. Artifacts (.cartography)
8. Navigator (Query)

Edges:
1. Input Repo -> Surveyor (static analysis, module graph, PageRank, git velocity)
2. Surveyor -> KnowledgeGraph (module graph nodes + imports)
3. Input Repo -> Hydrologist (SQL/Python/YAML lineage parsing)
4. Hydrologist -> KnowledgeGraph (lineage graph nodes + edges)
5. KnowledgeGraph -> Semanticist (purpose statements, doc drift, semantic index)
6. Semanticist -> KnowledgeGraph (annotations + day-one answers)
7. KnowledgeGraph -> Archivist (CODEBASE.md, onboarding_brief.md, trace)
8. Archivist -> Artifacts (.cartography outputs)
9. Artifacts -> Navigator (loads graphs + semantic index)
10. Navigator -> User (interactive queries + citations)

Layout suggestion:
- Left column: Input Repo
- Center column (top to bottom): Surveyor, Hydrologist, Semanticist, Archivist
- Right column: Artifacts
- Bottom: Navigator connected to Artifacts and User
- KnowledgeGraph should appear as a shared cylinder in the center, with arrows from Surveyor/Hydrologist/Semanticist to it, and from it to Archivist.

Labels to include on boxes:
- Surveyor: module graph, PageRank, git velocity, dead code
- Hydrologist: lineage graph, sources/sinks, blast radius
- Semanticist: purpose statements, doc drift, semantic index, Day-One answers
- Archivist: CODEBASE.md, onboarding brief, trace log
- Navigator: query tools (find_implementation, trace_lineage, blast_radius, explain_module)

Notes:
- Emphasize that KnowledgeGraph is the shared internal representation.
- Emphasize that artifacts are written to `<repo>/.cartography/`.

