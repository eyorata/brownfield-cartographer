# CODEBASE.md

Generated: 2026-03-14T13:27:33Z
Target repo: C:\Users\user\Documents\brownfield-cartographer\brownfield-cartographer\_targets\Roo-Code

## Architecture Overview
- Module graph: nodes=1759, edges=2326
- Lineage graph: nodes=18, edges=17
- LLM usage: used_tokens=0 / max_total_tokens=200000

## Critical Path
- High-centrality modules (PageRank):
  - packages/types/src/providers/../model.ts (pagerank=0.009036, velocity_30d=0, dead=False)
  - webview-ui/src/components/settings/providers/../transforms.ts (pagerank=0.006606, velocity_30d=0, dead=False)
  - apps/cli/src/ui/components/../theme.ts (pagerank=0.003201, velocity_30d=0, dead=False)
  - apps/cli/src/agent/agent-state.ts (pagerank=0.002878, velocity_30d=1, dead=False)
  - packages/vscode-shim/src/classes/../types.ts (pagerank=0.002832, velocity_30d=0, dead=False)
  - webview-ui/src/components/settings/SettingsView.tsx (pagerank=0.002663, velocity_30d=1, dead=False)
  - src/api/providers/../../shared/api.ts (pagerank=0.002596, velocity_30d=0, dead=False)
  - src/core/tools/../../shared/tools.ts (pagerank=0.002538, velocity_30d=0, dead=False)
  - webview-ui/src/components/settings/providers/../ModelPicker.tsx (pagerank=0.002386, velocity_30d=0, dead=False)
  - packages/types/src/provider-settings.ts (pagerank=0.002365, velocity_30d=1, dead=False)
  - src/core/tools/../task/Task.ts (pagerank=0.002360, velocity_30d=0, dead=False)
  - apps/cli/src/ui/components/autocomplete/triggers/../types.ts (pagerank=0.002328, velocity_30d=0, dead=False)
  - src/integrations/terminal/types.ts (pagerank=0.002298, velocity_30d=1, dead=False)
  - packages/evals/src/cli/../db/index.ts (pagerank=0.002249, velocity_30d=0, dead=False)
  - src/api/providers/../index.ts (pagerank=0.002151, velocity_30d=0, dead=False)

## Data Sources & Sinks
- Sources (in-degree 0 datasets):
  - runs
  - tasks_language_exercise_idx
  - tasks_task_metrics_id_taskMetrics_id_fk
  - public.taskMetrics
  - toolErrors_run_id_runs_id_fk
  - tasks_run_id_runs_id_fk
  - toolErrors
  - public.runs
  - public.tasks
  - toolErrors_task_id_tasks_id_fk
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
- packages/types/src/providers/../model.ts [the-string]: packages/types/src/providers/../model.ts is a source file.
- webview-ui/src/components/settings/providers/../transforms.ts [value-const]: webview-ui/src/components/settings/providers/../transforms.ts is a source file.
- apps/cli/src/ui/components/../theme.ts [const-text]: apps/cli/src/ui/components/../theme.ts is a source file.
- apps/cli/src/agent/agent-state.ts [the-string]: apps/cli/src/agent/agent-state.ts is a source file.
- packages/vscode-shim/src/classes/../types.ts [string-export]: packages/vscode-shim/src/classes/../types.ts is a source file.
- webview-ui/src/components/settings/SettingsView.tsx [type-const]: webview-ui/src/components/settings/SettingsView.tsx is a source file.
- src/api/providers/../../shared/api.ts [string-export]: src/api/providers/../../shared/api.ts is a source file.
- src/core/tools/../../shared/tools.ts [string-export]: src/core/tools/../../shared/tools.ts is a source file.
- webview-ui/src/components/settings/providers/../ModelPicker.tsx [type-const]: webview-ui/src/components/settings/providers/../ModelPicker.tsx is a source file.
- packages/types/src/provider-settings.ts [const-text]: packages/types/src/provider-settings.ts is a source file.
- src/core/tools/../task/Task.ts [type-const]: src/core/tools/../task/Task.ts is a source file.
- apps/cli/src/ui/components/autocomplete/triggers/../types.ts [the-string]: apps/cli/src/ui/components/autocomplete/triggers/../types.ts is a source file.
- src/integrations/terminal/types.ts [string-export]: src/integrations/terminal/types.ts is a source file.
- packages/evals/src/cli/../db/index.ts [export-const]: packages/evals/src/cli/../db/index.ts is a source file.
- src/api/providers/../index.ts [the-string]: src/api/providers/../index.ts is a source file.
- src/api/providers/../transform/stream.ts [string-export]: src/api/providers/../transform/stream.ts is a source file.
- apps/cli/src/ui/components/tools/../Icon.tsx [the-string]: apps/cli/src/ui/components/tools/../Icon.tsx is a source file.
- src/services/code-index/interfaces/vector-store.ts [the-string]: src/services/code-index/interfaces/vector-store.ts is a source file.
- webview-ui/src/components/settings/SectionHeader.tsx [classname-div]: webview-ui/src/components/settings/SectionHeader.tsx is a source file.
- apps/web-roo-code/src/lib/blog/types.ts [string-export]: apps/web-roo-code/src/lib/blog/types.ts is a source file.
- src/utils/../shared/package.ts [the-string]: src/utils/../shared/package.ts is a source file.
- apps/cli/src/agent/events.ts [the-string]: apps/cli/src/agent/events.ts is a source file.
- apps/cli/src/lib/storage/index.ts [export-const]: apps/cli/src/lib/storage/index.ts is a source file.
- packages/types/src/model.ts [the-string]: packages/types/src/model.ts is a source file.
- apps/vscode-e2e/src/suite/utils.ts [const-error]: apps/vscode-e2e/src/suite/utils.ts is a source file.
- apps/vscode-e2e/src/suite/tools/../utils.ts [const-error]: apps/vscode-e2e/src/suite/tools/../utils.ts is a source file.
- apps/vscode-e2e/src/suite/tools/../test-utils.ts [string-export]: apps/vscode-e2e/src/suite/tools/../test-utils.ts is a source file.
- src/core/tools/BaseTool.ts [the-string]: src/core/tools/BaseTool.ts is a source file.
- webview-ui/src/components/common/IconButton.tsx [classname-div]: webview-ui/src/components/common/IconButton.tsx is a source file.
- packages/cloud/src/bridge/BaseChannel.ts [this-the]: packages/cloud/src/bridge/BaseChannel.ts is a source file.
- webview-ui/src/components/settings/Section.tsx [classname-div]: webview-ui/src/components/settings/Section.tsx is a source file.
- apps/web-roo-code/src/components/homepage/../ui/index.ts [export-const]: apps/web-roo-code/src/components/homepage/../ui/index.ts is a source file.
- packages/types/src/codebase-index.ts [string-export]: packages/types/src/codebase-index.ts is a source file.
- packages/core/src/worktree/types.ts [export-const]: packages/core/src/worktree/types.ts is a source file.
- webview-ui/src/components/settings/../common/FormattedTextField.tsx [value-const]: webview-ui/src/components/settings/../common/FormattedTextField.tsx is a source file.
- webview-ui/src/components/settings/SearchableSetting.tsx [classname-div]: webview-ui/src/components/settings/SearchableSetting.tsx is a source file.
- webview-ui/src/components/settings/useSettingsSearch.ts [const-text]: webview-ui/src/components/settings/useSettingsSearch.ts is a source file.
- src/core/tools/../prompts/responses.ts [the-string]: src/core/tools/../prompts/responses.ts is a source file.
- packages/evals/src/cli/utils.ts [this-the]: packages/evals/src/cli/utils.ts is a source file.
- webview-ui/src/components/chat/LucideIconButton.tsx [classname-div]: webview-ui/src/components/chat/LucideIconButton.tsx is a source file.
- apps/cli/src/ui/utils/../types.ts [string-export]: apps/cli/src/ui/utils/../types.ts is a source file.
- webview-ui/src/components/chat/../common/MarkdownBlock.tsx [type-const]: webview-ui/src/components/chat/../common/MarkdownBlock.tsx is a source file.
- src/api/providers/base-provider.ts [const-text]: src/api/providers/base-provider.ts is a source file.
- packages/evals/src/db/../exercises/index.ts [const-error]: packages/evals/src/db/../exercises/index.ts is a source file.
- apps/cli/src/ui/components/tools/../../types.ts [string-export]: apps/cli/src/ui/components/tools/../../types.ts is a source file.
- apps/web-roo-code/public/heroes/agent-reviewer.png [value-const]: apps/web-roo-code/public/heroes/agent-reviewer.png is a source file.
- webview-ui/src/components/history/types.ts [the-string]: webview-ui/src/components/history/types.ts is a source file.
- webview-ui/src/components/chat/IconButton.tsx [classname-div]: webview-ui/src/components/chat/IconButton.tsx is a source file.
- src/utils/logging/types.ts [the-string]: src/utils/logging/types.ts is a source file.
- apps/web-roo-code/src/app/evals/types.ts [string-export]: apps/web-roo-code/src/app/evals/types.ts is a source file.
- packages/types/src/tool.ts [const-text]: packages/types/src/tool.ts is a source file.
- src/api/providers/utils/../../../i18n/setup.ts [const-error]: src/api/providers/utils/../../../i18n/setup.ts is a source file.
- packages/cloud/src/retry-queue/types.ts [string-export]: packages/cloud/src/retry-queue/types.ts is a source file.
- packages/vscode-shim/src/classes/../interfaces/workspace.ts [string-export]: packages/vscode-shim/src/classes/../interfaces/workspace.ts is a source file.
- apps/cli/src/ui/hooks/../store.ts [string-export]: apps/cli/src/ui/hooks/../store.ts is a source file.
- packages/core/src/message-utils/safeJsonParse.ts [the-string]: packages/core/src/message-utils/safeJsonParse.ts is a source file.
- apps/vscode-e2e/src/suite/test-utils.ts [export-const]: apps/vscode-e2e/src/suite/test-utils.ts is a source file.
- webview-ui/src/components/settings/types.ts [type-const]: webview-ui/src/components/settings/types.ts is a source file.
- src/api/providers/../../shared/package.ts [the-string]: src/api/providers/../../shared/package.ts is a source file.
- src/activate/../core/webview/ClineProvider.ts [type-const]: src/activate/../core/webview/ClineProvider.ts is a source file.

## Artifacts
- module graph: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/0e1d60e299c9/module_graph.json`
- lineage graph: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/0e1d60e299c9/lineage_graph.json`
- semantic index: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/0e1d60e299c9/semantic_index.json`
- onboarding brief: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/0e1d60e299c9/onboarding_brief.md`
- trace: `C:/Users/user/Documents/brownfield-cartographer/brownfield-cartographer/.cartography/ui_runs/0e1d60e299c9/cartography_trace.jsonl`

