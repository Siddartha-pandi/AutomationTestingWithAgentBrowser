import { ChangeDetectorService } from './change-detector.service';

describe('ChangeDetectorService (Deterministic Similarity Engine)', () => {
  let service: ChangeDetectorService;

  beforeEach(() => {
    service = new ChangeDetectorService();
  });

  it('calculates exact match similarity as 1.0', () => {
    const sim = service.calculateLevenshteinSimilarity('submit-button', 'submit-button');
    expect(sim).toBe(1.0);
  });

  it('calculates case-insensitive similarity', () => {
    const sim = service.calculateLevenshteinSimilarity('Submit Order', 'submit order');
    expect(sim).toBe(1.0);
  });

  it('calculates minor typo similarity > 0.8', () => {
    const sim = service.calculateLevenshteinSimilarity('Confirm Purchase', 'Confrm Purchase');
    expect(sim).toBeGreaterThan(0.85);
  });

  it('calculates unrelated strings as low similarity', () => {
    const sim = service.calculateLevenshteinSimilarity('Delete Account', 'View Profile');
    expect(sim).toBeLessThan(0.4);
  });
});

