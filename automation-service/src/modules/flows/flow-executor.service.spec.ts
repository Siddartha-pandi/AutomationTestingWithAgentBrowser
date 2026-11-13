import { FlowExecutorService } from './flow-executor.service';

describe('FlowExecutorService (Variable Interpolation, Condition Evaluation & Validation)', () => {
  let service: FlowExecutorService;

  beforeEach(() => {
    service = new FlowExecutorService(
      {} as any,
      {} as any,
      {} as any,
      {} as any,
      {} as any,
    );
  });

  it('interpolates single variable in string', () => {
    const res = service.interpolateVariables('https://{{HOST}}/api', { HOST: 'example.com' });
    expect(res).toBe('https://example.com/api');
  });

  it('interpolates multiple variables in string', () => {
    const res = service.interpolateVariables('Hello {{FIRST_NAME}} {{LAST_NAME}}!', {
      FIRST_NAME: 'Alice',
      LAST_NAME: 'Smith',
    });
    expect(res).toBe('Hello Alice Smith!');
  });

  it('evaluates equality conditions accurately', () => {
    expect(service.evaluateCondition({ variable: '{{status}}', operator: '==', value: 'active' }, { status: 'active' })).toBe(true);
    expect(service.evaluateCondition({ variable: '{{status}}', operator: '==', value: 'inactive' }, { status: 'active' })).toBe(false);
  });

  it('evaluates numeric comparisons accurately', () => {
    expect(service.evaluateCondition({ left_operand: '{{count}}', operator: '>', right_operand: 5 }, { count: 10 })).toBe(true);
    expect(service.evaluateCondition({ left_operand: '{{count}}', operator: '<', right_operand: 5 }, { count: 10 })).toBe(false);
  });

  it('validates graph detects missing source or target edges', () => {
    const invalidGraph = {
      nodes: [{ id: 'node-1', type: 'navigate', config: { url: 'https://example.com' } }],
      edges: [{ source: 'node-1', target: 'non-existent-target' }],
    };

    const report = service.validateGraph(invalidGraph as any);
    expect(report.valid).toBe(false);
    expect(report.errors[0]).toContain('non-existent target');
  });

  it('topologically sorts a linear DAG correctly', () => {
    const graph = {
      nodes: [
        { id: 'node-3', type: 'assert', config: {} },
        { id: 'node-1', type: 'navigate', config: { url: 'https://example.com' } },
        { id: 'node-2', type: 'click', config: {} },
      ],
      edges: [
        { source: 'node-1', target: 'node-2' },
        { source: 'node-2', target: 'node-3' },
      ],
    };

    const sorted = service.topologicalSort(graph);
    expect(sorted.map((n) => n.id)).toEqual(['node-1', 'node-2', 'node-3']);
  });
});
