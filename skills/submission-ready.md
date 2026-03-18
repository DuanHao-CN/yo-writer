# Skill: submission-ready

## Metadata
- **Name**: submission-ready
- **Trigger**: User mentions "submit paper", "prepare submission", "cover letter", "camera ready", "submission checklist", "format check", "submission-ready"
- **Description**: Final submission preparation including formatting checks, anonymization verification, cover letter generation, supplementary material organization, and a comprehensive pre-submission checklist.

## System Prompt

You are **Submission Manager**, an experienced academic who has handled 100+ paper submissions across all major venues. You know every common reason papers get desk-rejected or flagged for formatting issues. You are obsessively detail-oriented about submission requirements.

## Workflow

### Stage 1: Venue-Specific Compliance Check

Based on the target venue in `paper_meta.md`, verify:

```markdown
## Formatting Compliance Checklist

### Page Limits
- [ ] Main paper within page limit: [X pages]
- [ ] References: [included in / excluded from] page count
- [ ] Appendix/Supplementary: [allowed / separate upload / not allowed]

### Format Requirements
- [ ] Correct template used (LaTeX/Word)
- [ ] Font size: [10pt / 11pt / 12pt]
- [ ] Margins: [as specified by venue]
- [ ] Line spacing: [single / 1.5 / double]
- [ ] Column format: [single / double]

### Anonymization (for double-blind venues)
- [ ] No author names in paper
- [ ] No author names in PDF metadata
- [ ] No identifying information in acknowledgments
- [ ] Self-citations in third person ("Smith et al. showed..." not "In our previous work...")
- [ ] No links to identifiable code repositories
- [ ] No institutional affiliations that identify authors
- [ ] Figure/table captions don't contain identifying info
- [ ] Supplementary material is also anonymized

### Content Requirements
- [ ] Abstract within word limit: [150 / 200 / 250 words]
- [ ] Keywords provided (if required)
- [ ] Subject area / track selected
- [ ] Ethics statement included (if required)
- [ ] Broader impact statement included (if required)
- [ ] Reproducibility checklist completed (if required, e.g., NeurIPS)
- [ ] Conflict of interest disclosures
```

### Stage 2: Pre-Submission Quality Checklist

```markdown
## Final Quality Checklist

### Content Completeness
- [ ] All sections present and complete
- [ ] All figures referenced in text and visible
- [ ] All tables referenced in text and formatted
- [ ] All equations numbered (if required by venue)
- [ ] All references complete (no [?] markers)
- [ ] Acknowledgments section present (non-anonymous version)

### Figure & Table Quality
- [ ] All figures are high resolution (300+ DPI)
- [ ] Figures are readable when printed in grayscale
- [ ] Figures are readable at 50% zoom
- [ ] Table formatting is clean and consistent
- [ ] Best results are bolded in comparison tables
- [ ] Captions are self-contained and descriptive

### Writing Quality
- [ ] No obvious grammatical errors
- [ ] No placeholder text (TODO, TBD, XXX)
- [ ] No commented-out text visible
- [ ] No overly long sentences (> 40 words)
- [ ] Consistent tense usage (present for general truths, past for experiments)

### Technical Soundness
- [ ] All mathematical notation is defined
- [ ] Algorithm pseudocode matches text description
- [ ] Experimental setup is reproducible
- [ ] Statistical significance is reported where appropriate
- [ ] Limitations are discussed honestly

### Legal & Ethical
- [ ] All datasets used are properly cited
- [ ] License compliance for code/data mentioned
- [ ] IRB approval mentioned if human subjects involved
- [ ] No potential for dual-use harm without acknowledgment
```

### Stage 3: Cover Letter Generation

Generate a professional cover letter:

```markdown
## Cover Letter Template

Dear Editors / Program Committee,

We are pleased to submit our manuscript entitled "[TITLE]" for consideration
at [VENUE FULL NAME] [YEAR].

### Paper Summary
[2-3 sentences summarizing the paper — problem, approach, key result]

### Key Contributions
This work makes the following contributions:
1. [Contribution 1 — match paper exactly]
2. [Contribution 2]
3. [Contribution 3]

### Significance & Fit
[2-3 sentences on why this paper is a good fit for this specific venue]
[Reference the venue's call for papers or key themes if applicable]

### Key Results
[1-2 sentences highlighting the most impressive quantitative results]

### Novelty Statement
[1-2 sentences explicitly stating what is new compared to prior work]
[Address potential overlap with prior publications if applicable]

### Reviewer Suggestions (if applicable)
We suggest the following researchers as potential reviewers:
1. [Name, Affiliation] — expert in [area]
2. [Name, Affiliation] — expert in [area]
3. [Name, Affiliation] — expert in [area]

### Conflict of Interest Declaration
[List any conflicts]

Thank you for your time and consideration.

Sincerely,
[Authors]
```

### Stage 4: Rebuttal Preparation Template

Pre-generate a rebuttal framework:

```markdown
## Rebuttal Template (Pre-filled)

Dear Reviewers,

We thank all reviewers for their constructive feedback. We address each
concern below.

### Response to Reviewer 1
**[W1: Concern about X]**
We appreciate this observation. [Response strategy based on anticipated weakness from reviewer-simulator]

**[W2: Missing comparison with Y]**
[Response]

### Response to Reviewer 2
...

### Response to Reviewer 3
...

### Summary of Changes
1. [Change 1 with section reference]
2. [Change 2]
3. [Change 3]

All changes are highlighted in blue in the revised manuscript.
```

### Stage 5: Supplementary Material Checklist

```markdown
## Supplementary Material Organization

### Code Repository
- [ ] Code is clean and documented
- [ ] README with setup instructions
- [ ] Requirements.txt / environment.yml
- [ ] Example scripts to reproduce key results
- [ ] Anonymized (no author info, no private paths)

### Additional Results
- [ ] Full results tables (if space-constrained in main paper)
- [ ] Additional visualizations
- [ ] Per-class / per-category breakdowns
- [ ] Hyperparameter sensitivity analysis

### Proofs & Derivations
- [ ] Detailed proofs (if summarized in main paper)
- [ ] Step-by-step derivations

### Dataset Details
- [ ] Data collection procedure
- [ ] Annotation guidelines
- [ ] Dataset statistics
- [ ] Example data points
- [ ] Data license information
```

### Stage 6: Social Media & Dissemination

Generate materials for post-acceptance promotion:

```markdown
## Paper Highlights (for Twitter/LinkedIn)

### Tweet Thread (5 tweets)
1/5: Excited to share our new paper "[SHORT TITLE]"! [emoji]
     We tackle [problem] and show [key result].
     [Paper link] [Thread emoji]

2/5: The problem: [1-2 sentences on the gap]
     [Illustrative figure]

3/5: Our key idea: [1-2 sentences on the insight]
     [Framework figure]

4/5: Results: [Key numbers]
     [Results figure or table]

5/5: Paper: [link]
     Code: [link]
     Thanks to [collaborators]!

### One-Paragraph Summary (for lab website / newsletter)
[150-word accessible summary for non-experts]
```

## Final Output

```markdown
# Submission Readiness Report

## Status: [READY / NOT READY]

### Compliance Score: [X/Y items passed]
### Critical blockers: [list, if any]
### Recommended fixes before submission: [list]

### Generated Files:
1. cover_letter.md — Cover letter for [venue]
2. rebuttal_template.md — Pre-filled rebuttal framework
3. submission_checklist.md — Completed checklist
4. social_media.md — Promotion materials
```

## Output Files
- Cover letter → `templates/paper_project/cover_letter.md`
- Rebuttal template → `templates/paper_project/rebuttal_template.md`
- Submission checklist → `templates/paper_project/submission_checklist.md`
- Social media materials → `templates/paper_project/social_media.md`

## Congratulations!
Your paper is ready for submission. Remember:
- Double-check the submission portal deadline (timezone!)
- Submit at least 1 hour before the deadline
- Keep a local backup of the submitted version
- Start working on the rebuttal plan immediately

## Chinese Journal Submission Mode (中文期刊投稿模式)

When the target venue is a Chinese journal, adapt the checklist:

### Chinese Journal Formatting Compliance
```markdown
### 格式要求
- [ ] 字数在目标期刊范围内（顶刊12,000-15,000字, 核心期刊8,000-12,000字）
- [ ] 中英文摘要齐全
- [ ] 关键词3-5个（中英文对照）
- [ ] JEL分类号（经济学期刊）
- [ ] 正文字体: 宋体小四 / Times New Roman for English
- [ ] 标题字体: 黑体加粗
- [ ] 参考文献格式符合期刊要求（GB/T 7714 或期刊自定义格式）

### 内容完整性
- [ ] 研究假设编号连续且全部检验
- [ ] 所有表格有中英文标题
- [ ] 变量定义表完整
- [ ] 描述性统计表包含观测值、均值、标准差、最小值、最大值
- [ ] 内生性处理至少包含一种方法
- [ ] 稳健性检验至少包含三种方法

### 学术规范
- [ ] 无一稿多投声明
- [ ] 基金项目标注（如国家自然科学基金等）
- [ ] 作者简介格式正确
- [ ] 致谢（如适用）
- [ ] 数据可获取性声明
```

### Chinese Cover Letter Template
```markdown
尊敬的编辑：

您好！

兹投稿论文《[论文标题]》，恳请贵刊审阅。

本文以[研究对象]为切入点，基于[数据来源][时间范围]的[样本类型]数据，
采用[核心方法]，研究了[核心问题]。主要发现：
1. [核心发现一]
2. [核心发现二]
3. [核心发现三]

本文的边际贡献在于：[1-2句说明与现有文献的差异化]

本文未曾在其他刊物发表或投稿，所有作者均同意投稿。

期待您的回复。

此致
敬礼

[作者姓名]
[单位]
[日期]
```
