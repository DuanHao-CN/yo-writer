# CLAUDE.md — Yo-Writer: AI Academic Paper Writing System

## Project Overview
Yo-Writer is an AI-assisted academic paper writing system built on a **Skill + Workflow** architecture.
It provides **9 specialized skills** covering the full lifecycle from research planning to submission.
Supports **multiple languages** (English, Chinese) and **multiple disciplines** (ML/AI, Economics, Finance, Management).

## Project Structure
```
yo-writer/
  CLAUDE.md                     # This file - project memory & conventions
  skills/                       # 9 core writing skills
    paper-architect.md          # Skill 1: Paper planning & scaffolding (multi-discipline)
    literature-mapper.md        # Skill 2: Literature survey & gap analysis (multi-discipline)
    data-engineer.md            # Skill 3: Data checklist & processing code (NEW)
    section-writer.md           # Skill 4: Section-by-section writing engine (multi-language)
    consistency-guardian.md      # Skill 5: Cross-paper consistency checking
    story-polisher.md           # Skill 6: Narrative & language polishing + export
    reviewer-simulator.md       # Skill 7: Simulated peer review (multi-venue)
    submission-ready.md         # Skill 8: Submission preparation & checklist (multi-venue)
    revision-handler.md         # Skill 9: Post-review revision management (NEW)
  templates/
    paper_project/              # Starter template for a new paper
      paper_meta.md             # Metadata: title, contributions, symbols, terms
      outline.md                # Detailed section-level outline
      data_checklist.md          # Data collection & variable checklist
      code/                     # Data processing scripts (Stata/Python/R)
      sections/                 # Individual chapter files
        abstract.md
        introduction.md
        related_work.md
        method.md
        experiments.md
        discussion.md
        conclusion.md
        # Chinese economics papers may also include:
        # literature_review.md, empirical_results.md, etc.
      figures/                  # Figure descriptions & planning
      tables/                   # Table data & formatting
      references/               # Citation management
        bibliography.md
```

## Workflow Pipeline (Execution Order)

```
Phase 1 [Planning]       → paper-architect → literature-mapper
Phase 2 [Data Prep]      → data-engineer (empirical papers only)
Phase 3 [Writing]        → section-writer (per chapter)
Phase 4 [Refinement]     → consistency-guardian → story-polisher (+ optional export)
Phase 5 [QA & Revision]  → reviewer-simulator → (iterate if needed) → submission-ready
                          → (after review) revision-handler → back to Phase 4
```

**Rule**: Always complete Phase N before starting Phase N+1. Within a phase, follow left-to-right order.
**Note**: Phase 2 can be skipped for non-empirical papers (e.g., pure theory, survey papers).

## Global Writing Conventions

### Language & Style
- Default writing language: **Determined by target venue** (English for international venues, Chinese for Chinese journals)
- Academic tone: formal but clear, no colloquialisms
- One idea per paragraph; each paragraph starts with a topic sentence

**English Mode**:
- Prefer active voice for contributions ("We propose..."), passive voice for established facts ("X has been shown to...")
- No first-person singular ("I") — use "we" even for single-author papers
- Hedging language: "suggests", "indicates", "appears to"

**Chinese Mode (中文模式)**:
- 使用"本文"而非"我们"或"我"
- 学术规范用语, 避免口语化
- "表明/说明/证明" — 根据证据强度层级选择
- "显著" 仅用于统计显著性, 不用于一般修饰

**Both languages**:
- Avoid absolute claims without evidence: never use "always", "never", "clearly", "obviously"

### Structure Rules
- Every claim in Introduction must have corresponding evidence in Experiments
- Every design choice in Method must have motivation (why, not just what)
- Every component in Method must have corresponding ablation in Experiments
- Contributions listed in Introduction must match those summarized in Conclusion
- Numbers cited in Abstract must exactly match those in Experiments tables

### Section Length Targets

**English ML/AI Paper (8-10 pages)**:
| Section        | Words     | Pages (approx) |
|----------------|-----------|----------------|
| Abstract       | 150-300   | ~0.3           |
| Introduction   | 800-1500  | ~1.5           |
| Related Work   | 600-1200  | ~1.0           |
| Method         | 2000-3500 | ~2.5           |
| Experiments    | 2000-3000 | ~2.5           |
| Discussion     | 400-800   | ~0.5           |
| Conclusion     | 250-500   | ~0.5           |

**Chinese Economics Paper (12,000-15,000字)**:
| 章节             | 字数        | 占比    |
|-----------------|------------|---------|
| 摘要             | 300-500    | ~3%     |
| 一、引言          | 800-1500   | ~10%    |
| 二、文献综述       | 800-1200   | ~8%     |
| 三、理论分析       | 1000-1500  | ~10%    |
| 四、研究设计       | 1500-2000  | ~13%    |
| 五、实证结果       | 1500-2000  | ~13%    |
| 六、机制检验       | 800-1200   | ~8%     |
| 七、异质性分析     | 800-1200   | ~8%     |
| 八、结论          | 600-800    | ~5%     |

### Symbol & Terminology Management
- All mathematical symbols must be defined on first use
- Maintain a global symbol table in `paper_meta.md`
- Key terms: define on first use, then use consistently (no synonyms for technical terms)
- Abbreviations: spell out on first use, e.g., "Graph Neural Network (GNN)"

### Citation Conventions
- Use author-year in narrative: "Smith et al. (2024) proposed..."
- Use bracketed for parenthetical: "... has shown promise [Smith et al., 2024]"
- Cite 30-60 references for a typical top-venue paper
- Must include: seminal works + most recent 2 years of top-venue papers
- Related Work: cite by method groups, not chronologically

### Figure & Table Standards
- Every figure/table must be referenced in text
- Figures: vector format preferred; consistent color scheme; readable at 50% zoom
- Tables: bold the best result; include standard deviation where applicable
- Captions must be self-contained (reader should understand without reading body)

## Context Management Strategy

When writing a section, inject the following context:
1. **Always**: `paper_meta.md` (title, contributions, symbol table)
2. **Always**: `outline.md` (structural blueprint)
3. **Adjacent sections**: summary of the section before and after
4. **Never**: inject the full text of all sections simultaneously

This prevents context window overflow while maintaining coherence.

## Quality Gates

Before moving to the next phase, verify:

### After Phase 1 (Planning)
- [ ] Clear, single-sentence selling point defined
- [ ] 3 verifiable contribution points listed
- [ ] Story line logic chain has no gaps
- [ ] Target venue identified, length constraints known
- [ ] Writing language confirmed (English / Chinese)

### After Phase 2 (Data Prep — empirical papers only)
- [ ] Data checklist generated with all variables, sources, processing steps
- [ ] Instrumental variables documented with relevance & exogeneity arguments
- [ ] Processing code skeleton generated
- [ ] Sample size estimate is reasonable

### After Phase 3 (Writing)
- [ ] All sections drafted within target word counts
- [ ] Every contribution has corresponding method + experiment sections
- [ ] All figures and tables planned and referenced

### After Phase 4 (Refinement)
- [ ] Symbol/terminology consistency check passed
- [ ] Logic chain verified: Intro claims → Method designs → Experiment evidence
- [ ] No paragraph without a clear topic sentence
- [ ] Transitions between all sections are smooth
- [ ] (Chinese papers) 引言与文献综述无重复, 段落开头多样化

### After Phase 5 (QA)
- [ ] Simulated review score >= Weak Accept (English) or B/C+ (Chinese)
- [ ] All critical weaknesses addressed
- [ ] Formatting matches target venue requirements
- [ ] Cover letter drafted
- [ ] Export completed (docx / LaTeX as needed)

## Skill Invocation Quick Reference

| Task | Command |
|------|---------|
| Start a new paper | `paper-architect` |
| Survey literature | `literature-mapper` |
| Generate data checklist | `data-engineer` |
| Write a section | `section-writer --section <name>` |
| Check consistency | `consistency-guardian` |
| Polish narrative + export | `story-polisher` |
| Simulate review | `reviewer-simulator` |
| Prepare submission | `submission-ready` |
| Handle R&R revision | `revision-handler` |

## Important Reminders
- AI assists writing; humans own the ideas, data integrity, and academic ethics
- Never fabricate experimental results or citations
- Always verify AI-generated references against real publications
- The human author makes all final decisions on content and claims
