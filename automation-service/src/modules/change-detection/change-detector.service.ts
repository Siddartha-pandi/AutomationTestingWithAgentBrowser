import { Injectable, Logger } from '@nestjs/common';
import { Page } from 'playwright';

export interface SelectorBaseline {
  tag: string;
  role?: string;
  name?: string;
  label?: string;
  placeholder?: string;
  text?: string;
  stable_attributes: Record<string, string>;
  ancestor_path: string[];
}

export interface CandidateReplacement {
  generated_selector: string;
  strategy: 'role' | 'label' | 'test_id' | 'placeholder' | 'text' | 'css';
  confidence_score: number;
  scoring_breakdown: {
    tag_role_score: number;
    attributes_score: number;
    label_score: number;
    text_score: number;
    ancestor_score: number;
  };
  element_info: Record<string, any>;
}

@Injectable()
export class ChangeDetectorService {
  private readonly logger = new Logger(ChangeDetectorService.name);

  // Levenshtein similarity algorithm (0.0 to 1.0)
  calculateLevenshteinSimilarity(s1: string, s2: string): number {
    if (!s1 && !s2) return 1.0;
    if (!s1 || !s2) return 0.0;
    const a = s1.toLowerCase().trim();
    const b = s2.toLowerCase().trim();
    if (a === b) return 1.0;

    const matrix: number[][] = [];
    for (let i = 0; i <= b.length; i++) {
      matrix[i] = [i];
    }
    for (let j = 0; j <= a.length; j++) {
      matrix[0][j] = j;
    }

    for (let i = 1; i <= b.length; i++) {
      for (let j = 1; j <= a.length; j++) {
        if (b.charAt(i - 1) === a.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1, // substitution
            matrix[i][j - 1] + 1,     // insertion
            matrix[i - 1][j] + 1      // deletion
          );
        }
      }
    }

    const distance = matrix[b.length][a.length];
    const maxLen = Math.max(a.length, b.length);
    return maxLen === 0 ? 1.0 : (maxLen - distance) / maxLen;
  }

  async detectCandidates(
    page: Page,
    baseline: SelectorBaseline,
    minConfidence = 0.65,
  ): Promise<CandidateReplacement[]> {
    this.logger.log(`Evaluating deterministic candidate replacements for baseline: tag='${baseline.tag}', role='${baseline.role}'...`);

    // Extract interactive DOM elements from page
    const elementsData: any[] = await page.evaluate(() => {
      const candidates: any[] = [];
      const tags = ['button', 'input', 'a', 'select', 'textarea', '[role]', '[data-testid]', '[data-test]'];
      const nodes = Array.from(document.querySelectorAll(tags.join(',')));

      for (const node of nodes) {
        const el = node as HTMLElement;
        const rect = el.getBoundingClientRect();
        // Skip invisible or detached elements
        if (rect.width === 0 || rect.height === 0 || window.getComputedStyle(el).display === 'none') {
          continue;
        }

        const attrs: Record<string, string> = {};
        for (let i = 0; i < el.attributes.length; i++) {
          const a = el.attributes[i];
          attrs[a.name] = a.value;
        }

        // Collect ancestor tags
        const ancestors: string[] = [];
        let curr = el.parentElement;
        while (curr && ancestors.length < 5) {
          ancestors.push(curr.tagName.toLowerCase());
          curr = curr.parentElement;
        }

        candidates.push({
          tag: el.tagName.toLowerCase(),
          role: el.getAttribute('role') || el.tagName.toLowerCase(),
          name: el.getAttribute('aria-label') || el.getAttribute('name') || '',
          text: (el.innerText || '').substring(0, 100).trim(),
          placeholder: el.getAttribute('placeholder') || '',
          test_id: el.getAttribute('data-testid') || el.getAttribute('data-test') || '',
          attributes: attrs,
          ancestors,
        });
      }
      return candidates;
    });

    const evaluatedCandidates: CandidateReplacement[] = [];

    for (const el of elementsData) {
      // 1. Tag & Role score (weight: 0.30)
      const tagMatch = el.tag === baseline.tag ? 0.15 : 0;
      const roleMatch = (el.role && baseline.role && el.role === baseline.role) ? 0.15 : 0;
      const tag_role_score = tagMatch + roleMatch;

      // 2. Attributes score (weight: 0.25)
      let attrMatches = 0;
      let attrTotal = 0;
      for (const [key, val] of Object.entries(baseline.stable_attributes || {})) {
        attrTotal++;
        if (el.attributes[key] && el.attributes[key] === val) {
          attrMatches++;
        }
      }
      const attributes_score = (attrTotal > 0 ? (attrMatches / attrTotal) : 0.5) * 0.25;

      // 3. Label / Name score (weight: 0.20)
      const labelSim = this.calculateLevenshteinSimilarity(baseline.name || baseline.label || '', el.name || '');
      const label_score = labelSim * 0.20;

      // 4. Text score (weight: 0.15)
      const textSim = this.calculateLevenshteinSimilarity(baseline.text || '', el.text || '');
      const text_score = textSim * 0.15;

      // 5. Ancestor hierarchy Jaccard score (weight: 0.10)
      const baseAncestors = new Set<string>(baseline.ancestor_path || []);
      const elAncestors: string[] = Array.isArray(el.ancestors) ? el.ancestors : [];
      let intersection = 0;
      for (const a of elAncestors) {
        if (baseAncestors.has(a)) intersection++;
      }
      const union = new Set([...baseAncestors, ...elAncestors]).size;
      const ancestor_score = (union > 0 ? (intersection / union) : 0) * 0.10;

      const totalConfidence = tag_role_score + attributes_score + label_score + text_score + ancestor_score;

      if (totalConfidence >= minConfidence) {
        let generated_selector = '';
        let strategy: CandidateReplacement['strategy'] = 'css';

        if (el.test_id) {
          generated_selector = `[data-testid="${el.test_id}"]`;
          strategy = 'test_id';
        } else if (el.name) {
          generated_selector = `getByRole('${el.role}', { name: '${el.name}' })`;
          strategy = 'role';
        } else if (el.placeholder) {
          generated_selector = `getByPlaceholder('${el.placeholder}')`;
          strategy = 'placeholder';
        } else if (el.text) {
          generated_selector = `getByText('${el.text}', { exact: true })`;
          strategy = 'text';
        } else {
          generated_selector = `${el.tag}[name="${el.attributes['name'] || ''}"]`;
        }

        evaluatedCandidates.push({
          generated_selector,
          strategy,
          confidence_score: Math.round(totalConfidence * 1000) / 1000,
          scoring_breakdown: {
            tag_role_score: Math.round(tag_role_score * 1000) / 1000,
            attributes_score: Math.round(attributes_score * 1000) / 1000,
            label_score: Math.round(label_score * 1000) / 1000,
            text_score: Math.round(text_score * 1000) / 1000,
            ancestor_score: Math.round(ancestor_score * 1000) / 1000,
          },
          element_info: el,
        });
      }
    }

    // Sort descending by confidence score
    return evaluatedCandidates.sort((a, b) => b.confidence_score - a.confidence_score);
  }
}
