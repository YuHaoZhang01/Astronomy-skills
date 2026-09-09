---
name: sn-paper-writing
description: "Revise or structure supernova and transient astrophysics papers using corpus-derived paragraph progression, sentence choices, and evidence-calibrated claims. Use for theory, numerical methods, light-curve fitting, population comparisons, or explicitly requested writing-style distillation from local reference papers."
metadata:
  version: "2.0.0"
---

# Supernova Paper Writing

将超新星与暂现源论文已有材料组织成清楚的英文论证。默认使用本包已蒸馏的规则；分析说明使用用户语言，稿件语言遵循用户要求。

适合理论、数值方法、光变拟合和样本比较。规则来自有限且作者相关的语料，是可调整的写作偏好，不是 ApJ 官方要求或个人风格鉴定。目标明显不同时先判断哪些规则仍适用。

## 技术保真

- 保持原稿的 LaTeX 命令、数学环境、公式、变量、数值、单位、误差、区间、命题、引文命令与 keys、图表引用和标签、脚注、专有名称原样。
- 保留否定、条件、假设、不确定性和证据层级。不能把拟合一致写成唯一机制证明，也不能无故削弱已支持的直接判断。
- 只使用用户原稿或明确提供的研究材料；缺失结果、引用、方法依据或检验时指出缺项，不从范文补写。科学疑点单列给作者判断。
- 阅读参考语料时只输出结构与修辞描述，不引用、改写或复现其研究发现。论文全文、转换副本、图像、提取缓存和逐段证据账本保存在用户项目，不能混入可分发 skill。

## 使用已有规则

用户要求润色、重组或据已有材料起草时，读取 [writing_rules.md](references/writing_rules.md)。按稿型和当前章节选择规则；不要重启语料收集。明确要求采用本 skill 修订已构成采用授权，不重复询问。

1. 确认原稿、章节范围和写作目标；优先沿用已提供的信息。缺少原稿或研究材料时请求该输入，不生成看似真实的论文。
2. 每次完整处理一节。诊断各段的主任务、承接关系、证据层级和适用规则，再给全节修订与逐段变更说明。用户明确要求仅诊断或只给修订稿时按其范围输出。
3. 记录实际修改的段落、规则编号、理由，以及因技术保真而未修改的问题。不凭样式给出录用概率；没有实际前后对照时不报提升分数。
4. 对照原稿复核受保护内容。移动引文或条件可能改变支持关系时保留原位；跨章节搬移技术材料需在用户的结构重组范围内进行。

复杂的段落组织问题再读 [paragraph_patterns.md](references/paragraph_patterns.md)；语态、时态或衔接问题再读 [sentence_patterns.md](references/sentence_patterns.md)。遇到规则冲突或一刀切模板，查看 [rule_boundaries.md](references/rule_boundaries.md)。这些参考文件均独立于私人语料，可离线使用。

只收到 PDF 时使用可用的本地提取工具，检查分栏、跨页段落、页眉与公式。文本已有时无需转换器。技术文字不可靠时回原页或请求源稿；不要猜写公式。工具选择服从用户环境，技能不绑定某个 Python 路径或 PDF 服务。

## 更新或重新蒸馏

仅在用户明确要求添加语料、换目标或重新蒸馏时，读取 [distillation.md](references/distillation.md)。将新的写作信号与已有规则比较，逐条找证据与反例，保存可审阅的新规则。

仅要求蒸馏时，在产物完成后交付，不擅自修改稿件。若用户此前已经授权按这些材料修订，继续在已授权范围工作；否则等待其采用新规则并提供稿件。授权修订不等于授权对外发布论文或语料。

## 来源与范围

本包可独立使用，不依赖另行安装 journal-adapt。工作流参考其 MIT 许可项目，保留了技术保真和分节修订原则，并按全文证据修正了固定段序和绝对禁词要求。详细出处、已完成范围与未验证事项见 [provenance.md](references/provenance.md)；许可见 [LICENSE](LICENSE)。
