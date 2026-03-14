# CODEBASE.md

Generated: 2026-03-14T12:36:29Z
Target repo: C:\Users\user\Documents\brownfield-cartographer\brownfield-cartographer\_targets\Roo-Code

## Architecture Overview
- Module graph: nodes=2966, edges=3396
- Lineage graph: nodes=18, edges=17
- LLM usage: used_tokens=0 / max_total_tokens=200000

## Critical Path
- High-centrality modules (PageRank):
  - packages/types/src/providers/../model.ts (pagerank=0.005264, velocity_30d=0, dead=False)
  - src/integrations/terminal/__tests__/streamUtils/index.ts (pagerank=0.004315, velocity_30d=1, dead=False)
  - src/services/tree-sitter/__tests__/helpers.ts (pagerank=0.004309, velocity_30d=1, dead=False)
  - webview-ui/src/components/settings/providers/../transforms.ts (pagerank=0.003849, velocity_30d=0, dead=False)
  - src/services/tree-sitter/__tests__/../queries/index.ts (pagerank=0.003551, velocity_30d=0, dead=False)
  - src/api/providers/__tests__/../../../shared/api.ts (pagerank=0.002362, velocity_30d=0, dead=False)
  - src/services/tree-sitter/__tests__/../index.ts (pagerank=0.002281, velocity_30d=0, dead=False)
  - src/services/tree-sitter/__tests__/../queries/tsx.ts (pagerank=0.002074, velocity_30d=0, dead=False)
  - apps/cli/src/ui/components/../theme.ts (pagerank=0.001865, velocity_30d=0, dead=False)
  - apps/cli/src/agent/agent-state.ts (pagerank=0.001677, velocity_30d=1, dead=False)
  - packages/vscode-shim/src/classes/../types.ts (pagerank=0.001650, velocity_30d=0, dead=False)
  - webview-ui/src/components/settings/SettingsView.tsx (pagerank=0.001552, velocity_30d=1, dead=False)
  - src/api/providers/../../shared/api.ts (pagerank=0.001513, velocity_30d=0, dead=False)
  - src/integrations/terminal/__tests__/streamUtils/pwshStream.ts (pagerank=0.001500, velocity_30d=1, dead=False)
  - src/integrations/terminal/__tests__/streamUtils/cmdStream.ts (pagerank=0.001500, velocity_30d=1, dead=False)

## Data Sources & Sinks
- Sources (in-degree 0 datasets):
  - runs
  - tasks_language_exercise_idx
  - public.tasks
  - tasks_run_id_runs_id_fk
  - public.runs
  - toolErrors_run_id_runs_id_fk
  - public.taskMetrics
  - tasks_task_metrics_id_taskMetrics_id_fk
  - toolErrors_task_id_tasks_id_fk
  - toolErrors
- Sinks (out-degree 0 datasets):

## Known Debt
- Dead code candidates (heuristic: exported symbols with no importers):

## High-Velocity Files
- .changeset/README.md (touches=1)
- .changeset/changelog-config.js (touches=1)
- .changeset/config.json (touches=1)
- .dockerignore (touches=1)
- .env.sample (touches=1)
- .git-blame-ignore-revs (touches=1)
- .gitattributes (touches=1)
- .gitconfig (touches=1)
- .github/CODEOWNERS (touches=1)
- .github/ISSUE_TEMPLATE/bug_report.yml (touches=1)

## Module Purpose Index
- packages/types/src/providers/../model.ts [const-type]: packages/types/src/providers/../model.ts is a source file.
- src/integrations/terminal/__tests__/streamUtils/index.ts [the-string]: src/integrations/terminal/__tests__/streamUtils/index.ts is a source file.
- src/services/tree-sitter/__tests__/helpers.ts [path-string]: src/services/tree-sitter/__tests__/helpers.ts is a source file.
- webview-ui/src/components/settings/providers/../transforms.ts [webview-ui]: webview-ui/src/components/settings/providers/../transforms.ts is a source file.
- src/services/tree-sitter/__tests__/../queries/index.ts [export-type]: src/services/tree-sitter/__tests__/../queries/index.ts is a source file.
- src/api/providers/__tests__/../../../shared/api.ts [const-type]: src/api/providers/__tests__/../../../shared/api.ts is a source file.
- src/services/tree-sitter/__tests__/../index.ts [path-string]: src/services/tree-sitter/__tests__/../index.ts is a source file.
- src/services/tree-sitter/__tests__/../queries/tsx.ts [definition-name]: src/services/tree-sitter/__tests__/../queries/tsx.ts is a source file.
- apps/cli/src/ui/components/../theme.ts [const-type]: apps/cli/src/ui/components/../theme.ts is a source file.
- apps/cli/src/agent/agent-state.ts [the-string]: apps/cli/src/agent/agent-state.ts is a source file.
- packages/vscode-shim/src/classes/../types.ts [string-export]: packages/vscode-shim/src/classes/../types.ts is a source file.
- webview-ui/src/components/settings/SettingsView.tsx [const-type]: webview-ui/src/components/settings/SettingsView.tsx is a source file.
- src/api/providers/../../shared/api.ts [const-type]: src/api/providers/../../shared/api.ts is a source file.
- src/integrations/terminal/__tests__/streamUtils/pwshStream.ts [this-error]: src/integrations/terminal/__tests__/streamUtils/pwshStream.ts is a source file.
- src/integrations/terminal/__tests__/streamUtils/cmdStream.ts [this-error]: src/integrations/terminal/__tests__/streamUtils/cmdStream.ts is a source file.
- src/core/tools/../../shared/tools.ts [string-export]: src/core/tools/../../shared/tools.ts is a source file.
- src/integrations/terminal/__tests__/streamUtils/bashStream.ts [this-error]: src/integrations/terminal/__tests__/streamUtils/bashStream.ts is a source file.
- webview-ui/src/components/settings/providers/../ModelPicker.tsx [webview-ui]: webview-ui/src/components/settings/providers/../ModelPicker.tsx is a source file.
- packages/types/src/provider-settings.ts [const-type]: packages/types/src/provider-settings.ts is a source file.
- src/core/tools/../task/Task.ts [const-type]: src/core/tools/../task/Task.ts is a source file.
- apps/cli/src/ui/components/autocomplete/triggers/../types.ts [the-string]: apps/cli/src/ui/components/autocomplete/triggers/../types.ts is a source file.
- src/api/providers/__tests__/../bedrock.ts [const-type]: src/api/providers/__tests__/../bedrock.ts is a source file.
- src/integrations/terminal/types.ts [string-export]: src/integrations/terminal/types.ts is a source file.
- packages/evals/src/cli/../db/index.ts [export-type]: packages/evals/src/cli/../db/index.ts is a source file.
- src/core/webview/__tests__/../ClineProvider.ts [const-type]: src/core/webview/__tests__/../ClineProvider.ts is a source file.
- webview-ui/src/components/chat/__tests__/../ChatView.tsx [webview-ui]: webview-ui/src/components/chat/__tests__/../ChatView.tsx is a source file.
- src/api/providers/../index.ts [the-string]: src/api/providers/../index.ts is a source file.
- src/api/providers/../transform/stream.ts [string-export]: src/api/providers/../transform/stream.ts is a source file.
- apps/cli/src/ui/components/tools/../Icon.tsx [the-string]: apps/cli/src/ui/components/tools/../Icon.tsx is a source file.
- src/services/code-index/interfaces/vector-store.ts [the-string]: src/services/code-index/interfaces/vector-store.ts is a source file.
- webview-ui/src/components/settings/SectionHeader.tsx [webview-ui]: webview-ui/src/components/settings/SectionHeader.tsx is a source file.
- src/core/task/__tests__/../Task.ts [const-type]: src/core/task/__tests__/../Task.ts is a source file.
- apps/web-roo-code/src/lib/blog/types.ts [string-export]: apps/web-roo-code/src/lib/blog/types.ts is a source file.
- webview-ui/src/components/chat/__tests__/../ChatRow.tsx [webview-ui]: webview-ui/src/components/chat/__tests__/../ChatRow.tsx is a source file.
- src/services/glob/__tests__/../list-files.ts [path-string]: src/services/glob/__tests__/../list-files.ts is a source file.
- src/core/tools/__tests__/../../../shared/tools.ts [string-export]: src/core/tools/__tests__/../../../shared/tools.ts is a source file.
- src/utils/../shared/package.ts [the-string]: src/utils/../shared/package.ts is a source file.
- apps/cli/src/agent/events.ts [the-string]: apps/cli/src/agent/events.ts is a source file.
- apps/cli/src/lib/storage/index.ts [export-type]: apps/cli/src/lib/storage/index.ts is a source file.
- packages/types/src/model.ts [const-type]: packages/types/src/model.ts is a source file.
- apps/vscode-e2e/src/suite/utils.ts [const-type]: apps/vscode-e2e/src/suite/utils.ts is a source file.
- src/core/task/__tests__/../../webview/ClineProvider.ts [const-type]: src/core/task/__tests__/../../webview/ClineProvider.ts is a source file.
- apps/vscode-e2e/src/suite/tools/../utils.ts [const-type]: apps/vscode-e2e/src/suite/tools/../utils.ts is a source file.
- apps/vscode-e2e/src/suite/tools/../test-utils.ts [export-type]: apps/vscode-e2e/src/suite/tools/../test-utils.ts is a source file.
- src/core/tools/BaseTool.ts [the-string]: src/core/tools/BaseTool.ts is a source file.
- webview-ui/src/components/common/IconButton.tsx [webview-ui]: webview-ui/src/components/common/IconButton.tsx is a source file.
- packages/cloud/src/bridge/BaseChannel.ts [this-error]: packages/cloud/src/bridge/BaseChannel.ts is a source file.
- webview-ui/src/components/settings/Section.tsx [webview-ui]: webview-ui/src/components/settings/Section.tsx is a source file.
- src/core/webview/__tests__/../webviewMessageHandler.ts [const-type]: src/core/webview/__tests__/../webviewMessageHandler.ts is a source file.
- apps/web-roo-code/src/components/homepage/../ui/index.ts [export-type]: apps/web-roo-code/src/components/homepage/../ui/index.ts is a source file.
- packages/types/src/codebase-index.ts [string-export]: packages/types/src/codebase-index.ts is a source file.
- packages/core/src/worktree/types.ts [export-type]: packages/core/src/worktree/types.ts is a source file.
- packages/vscode-shim/src/__tests__/../classes/Uri.ts [path-string]: packages/vscode-shim/src/__tests__/../classes/Uri.ts is a source file.
- src/services/code-index/embedders/__tests__/../openai-compatible.ts [this-error]: src/services/code-index/embedders/__tests__/../openai-compatible.ts is a source file.
- webview-ui/src/components/settings/../common/FormattedTextField.tsx [webview-ui]: webview-ui/src/components/settings/../common/FormattedTextField.tsx is a source file.
- webview-ui/src/components/settings/SearchableSetting.tsx [webview-ui]: webview-ui/src/components/settings/SearchableSetting.tsx is a source file.
- webview-ui/src/components/settings/useSettingsSearch.ts [webview-ui]: webview-ui/src/components/settings/useSettingsSearch.ts is a source file.
- src/core/tools/../prompts/responses.ts [the-string]: src/core/tools/../prompts/responses.ts is a source file.
- packages/evals/src/cli/utils.ts [this-error]: packages/evals/src/cli/utils.ts is a source file.
- webview-ui/src/components/chat/LucideIconButton.tsx [classname-div]: webview-ui/src/components/chat/LucideIconButton.tsx is a source file.

## Artifacts
- module graph: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/3a3b3ca3d538/module_graph.json`
- lineage graph: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/3a3b3ca3d538/lineage_graph.json`
- semantic index: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/3a3b3ca3d538/semantic_index.json`
- onboarding brief: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/3a3b3ca3d538/onboarding_brief.md`
- trace: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/3a3b3ca3d538/cartography_trace.jsonl`

