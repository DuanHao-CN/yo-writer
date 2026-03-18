# Yo-Writer: AI Academic Paper Writing System

An AI-assisted academic paper writing system built on a **Skill + Workflow** architecture, designed to guide you from initial research idea to submission-ready manuscript.

**Supports**: Multiple languages (English, 中文) | Multiple disciplines (ML/AI, Economics, Finance, Management)

## Quick Start

```
1. Tell AI: "I want to write a paper about [your topic]"
   -> Triggers: paper-architect (5-round planning)

2. Tell AI: "Survey the literature for my paper"
   -> Triggers: literature-mapper (citation landscape)

3. Tell AI: "Generate a data collection checklist"        ← NEW
   -> Triggers: data-engineer (variables + processing code)

4. Tell AI: "Write the [introduction/method/experiments]"
   -> Triggers: section-writer (per-section drafting)

5. Tell AI: "Check my paper for consistency"
   -> Triggers: consistency-guardian (6-dimension audit)

6. Tell AI: "Polish my paper's story and export to docx"   ← UPDATED
   -> Triggers: story-polisher (4-level polish + export)

7. Tell AI: "Simulate a peer review"
   -> Triggers: reviewer-simulator (3-reviewer panel)

8. Tell AI: "Prepare for submission"
   -> Triggers: submission-ready (checklist + cover letter)

9. Tell AI: "Handle the reviewer comments"                 ← NEW
   -> Triggers: revision-handler (R&R management)
```

## System Architecture

```
yo-writer/
  CLAUDE.md                          # Project memory and writing conventions
  README.md                          # This file
  skills/                            # 9 core writing skills
    paper-architect.md               # Phase 1: Planning and scaffolding
    literature-mapper.md             # Phase 1: Literature survey
    data-engineer.md                 # Phase 2: Data checklist & processing (NEW)
    section-writer.md                # Phase 3: Section-by-section writing
    consistency-guardian.md          # Phase 4: Consistency audit
    story-polisher.md               # Phase 4: Narrative polish + export
    reviewer-simulator.md           # Phase 5: Simulated peer review
    submission-ready.md             # Phase 5: Submission preparation
    revision-handler.md             # Phase 5+: Post-review revision (NEW)
  templates/
    paper_project/                   # Paper workspace template
      paper_meta.md                  # Title, contributions, symbols
      outline.md                     # Detailed section outline
      data_checklist.md              # Data collection & variable checklist
      code/                          # Data processing scripts (Stata/Python/R)
      sections/                      # Individual chapter files
      figures/                       # Figure planning
      tables/                        # Table data
      references/
        bibliography.md              # Citation management
```

## Workflow Pipeline

```
Phase 1          Phase 2          Phase 3          Phase 4           Phase 5
PLANNING         DATA PREP        WRITING          REFINEMENT        QA & REVISION
+-----------+    +-----------+    +-----------+    +-------------+   +-------------+
| paper-    |    | data-     |    | section-  |    | consistency-|   | reviewer-   |
| architect |--->| engineer  |--->| writer    |--->| guardian    |-->| simulator   |
|           |    | (empirical|    | (per      |    |             |   |             |
| literature|    |  papers)  |    |  section) |    | story-      |   | submission- |
| -mapper   |    +-----------+    +-----------+    | polisher    |   | ready       |
+-----------+                                      | (+ export)  |   |             |
                                                   +-------------+   | revision-   |
                                                         ^           | handler     |
                                                         |           +------+------+
                                                         |                  |
                                                         +------ (R&R) -----+
```

## The 9 Skills

| # | Skill | Role | Key Output |
|---|-------|------|------------|
| 1 | **paper-architect** | Research planning and paper scaffolding | paper_meta.md + outline.md |
| 2 | **literature-mapper** | Literature survey and gap analysis | Literature map + Related Work draft |
| 3 | **data-engineer** ⭐ | Data checklist and processing code | data_checklist.md + Stata/Python scripts |
| 4 | **section-writer** | Section-by-section writing engine | Individual section drafts |
| 5 | **consistency-guardian** | 6-dimension consistency audit | Consistency report with fix list |
| 6 | **story-polisher** | 4-level narrative refinement + export | Polish report + revised sections + .docx |
| 7 | **reviewer-simulator** | 3-persona peer review simulation | Review report with scores |
| 8 | **submission-ready** | Pre-submission checklist and materials | Cover letter + checklists |
| 9 | **revision-handler** ⭐ | Post-review R&R revision management | Rebuttal letter + change log |

⭐ = New in v2.0

## Multi-Language & Multi-Discipline Support

### Supported Configurations

| Feature | English ML/AI | Chinese Economics |
|---------|--------------|-------------------|
| **Planning** | NeurIPS/CVPR template | 《经济研究》8-chapter template |
| **Structure** | 6 sections | 8 chapters (引言→文献综述→理论分析→研究设计→实证结果→机制检验→异质性分析→结论) |
| **Data** | Benchmarks & datasets | CSMAR, WIND, CNRDS, 统计年鉴 |
| **Writing** | English academic style | 中文学术规范 ("本文"代替"我们") |
| **Review** | ICLR 1-10 scale | 中文期刊 A/B/C/D/E 评级 |
| **Export** | LaTeX (.tex) | Word (.docx) with 宋体/黑体 |
| **Submission** | Double-blind cover letter | 中文投稿信 + 无一稿多投声明 |
| **Revision** | English point-by-point rebuttal | 中文逐条回复 + 蓝色标注修改 |

### Paper Structure Targets

**English ML/AI Paper (8-10 pages)**:

| Section | Word Count | Key Principle |
|---------|-----------|---------------|
| Abstract | 150-300 | Self-contained; 5-sentence formula |
| Introduction | 800-1500 | Inverted triangle; 3 contributions |
| Related Work | 600-1200 | By method family, not chronology |
| Method | 2000-3500 | Motivate before mechanism |
| Experiments | 2000-3000 | Every claim needs evidence |
| Discussion | 400-800 | Limitations = honesty = respect |
| Conclusion | 250-500 | Insight, not summary |

**Chinese Economics Paper (12,000-15,000字)**:

| 章节 | 字数 | 核心要求 |
|-----|------|---------|
| 引言 | 800-1500 | 现实背景 + 文献不足 + 贡献点 |
| 文献综述 | 800-1200 | 按主题分组, 明确定位 |
| 理论分析 | 1000-1500 | 逻辑链 + 可检验假设 |
| 研究设计 | 1500-2000 | 变量定义 + 模型设定 |
| 实证结果 | 1500-2000 | 基准回归 + 内生性 + 稳健性 |
| 机制检验 | 800-1200 | 每个渠道独立检验 |
| 异质性分析 | 800-1200 | 分组回归 + 组间差异检验 |
| 结论 | 600-800 | 发现 + 政策建议 + 局限 |

## Key Design Principles

1. **One Story**: Every paper tells ONE story. All sections serve that story.
2. **Multi-Discipline**: Adapts templates, structure, and conventions to the target field.
3. **Multi-Language**: Supports English and Chinese academic writing norms.
4. **Context Management**: Only inject relevant context per section to avoid overflow.
5. **Quality Gates**: Each phase has explicit pass/fail criteria.
6. **Full Lifecycle**: From planning through submission to post-review revision.
7. **Export Ready**: Built-in docx/LaTeX export with proper formatting.
8. **Human-in-the-Loop**: AI assists; humans own ideas, data, and ethics.

## Starting a New Paper

1. Copy `templates/paper_project/` to a new directory for your paper
2. Run `paper-architect` to fill in `paper_meta.md` and `outline.md`
3. Run `literature-mapper` to build the citation landscape
4. (Empirical papers) Run `data-engineer` to generate data checklist
5. Follow the workflow pipeline from Phase 3 to Phase 5
6. Use `story-polisher` with export to generate submission-ready document
7. Iterate between Phase 4-5 until reviewer score meets acceptance threshold

## Changelog

### v2.0 (2026-03-16) — Multi-Discipline Update
Based on real-world experience writing a Chinese economics paper (数字经济发展与企业创新质量):

**New Skills**:
- `data-engineer`: Generates data collection checklists, variable codebooks, and processing code (Stata/Python/R)
- `revision-handler`: Manages post-review R&R with point-by-point rebuttal letters and change tracking

**Updated Skills**:
- `paper-architect`: Added Chinese 8-chapter outline template for economics papers
- `literature-mapper`: Added Chinese economics literature mode with CNKI/知网 sources
- `section-writer`: Added complete Chinese economics section templates (引言→结论 all 8 chapters)
- `story-polisher`: Added Level 5 (Export & Merge) for docx/LaTeX output + Chinese polish rules
- `reviewer-simulator`: Added Chinese journal review mode with A-E scoring scale
- `submission-ready`: Added Chinese journal formatting checklist and cover letter template

**Workflow Changes**:
- Expanded from 4-phase to 5-phase pipeline (added Phase 2: Data Prep)
- Added revision feedback loop (Phase 5 → Phase 4 via revision-handler)
- Quality gates updated for each phase

### v1.0 — Initial Release
- 7 skills for English ML/AI paper writing
- 4-phase workflow pipeline

## License

MIT
