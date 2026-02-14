import React, { useState, useEffect } from 'react';
import './ReviewDashboard.css';

interface ReviewOutcome {
  id: string;
  prNumber: number;
  prTitle: string;
  author: string;
  timestamp: string;
  overallStatus: 'approved' | 'changes_requested' | 'in_progress' | 'blocked';
  reviewerInsights: ReviewerInsight[];
  competingReviews: CompetingReview[];
  metrics: ReviewMetrics;
}

interface ReviewerInsight {
  reviewerId: string;
  reviewerName: string;
  reviewerType: 'correctness' | 'security' | 'performance' | 'style';
  status: 'approved' | 'changes_requested' | 'commented';
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  findings: Finding[];
  timestamp: string;
  confidence: number;
}

interface Finding {
  id: string;
  title: string;
  description: string;
  file: string;
  line: number;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  category: string;
  suggestedFix?: string;
  challenged: boolean;
  challengeCount: number;
}

interface CompetingReview {
  id: string;
  challengerId: string;
  challengerName: string;
  targetReviewerId: string;
  targetFindingId: string;
  challengeType: 'false_positive' | 'severity_dispute' | 'alternative_solution' | 'context_missing';
  argument: string;
  evidence?: string;
  votes: number;
  resolution?: 'upheld' | 'overturned' | 'modified';
  timestamp: string;
}

interface ReviewMetrics {
  totalFindings: number;
  criticalFindings: number;
  challengedFindings: number;
  reviewerConsensus: number;
  estimatedFixTime: string;
  codeQualityScore: number;
}

const ReviewDashboard: React.FC = () => {
  const [reviews, setReviews] = useState<ReviewOutcome[]>([]);
  const [selectedReview, setSelectedReview] = useState<ReviewOutcome | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('timestamp');
  const [showCompeting, setShowCompeting] = useState<boolean>(false);
  const [expandedFindings, setExpandedFindings] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchReviews();
  }, []);

  const fetchReviews = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/reviews');
      const data = await response.json();
      setReviews(data);
      if (data.length > 0) {
        setSelectedReview(data[0]);
      }
    } catch (error) {
      console.error('Failed to fetch reviews:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'approved':
        return '#10b981';
      case 'changes_requested':
        return '#f59e0b';
      case 'blocked':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical':
        return '#dc2626';
      case 'high':
        return '#f59e0b';
      case 'medium':
        return '#eab308';
      case 'low':
        return '#3b82f6';
      default:
        return '#6b7280';
    }
  };

  const getReviewerTypeIcon = (type: string): string => {
    switch (type) {
      case 'correctness':
        return '✓';
      case 'security':
        return '🛡️';
      case 'performance':
        return '⚡';
      case 'style':
        return '🎨';
      default:
        return '📋';
    }
  };

  const toggleFinding = (findingId: string) => {
    const newExpanded = new Set(expandedFindings);
    if (newExpanded.has(findingId)) {
      newExpanded.delete(findingId);
    } else {
      newExpanded.add(findingId);
    }
    setExpandedFindings(newExpanded);
  };

  const filterReviewers = (insights: ReviewerInsight[]): ReviewerInsight[] => {
    let filtered = insights;
    
    if (filterType !== 'all') {
      filtered = filtered.filter(r => r.reviewerType === filterType);
    }
    
    if (filterSeverity !== 'all') {
      filtered = filtered.filter(r => 
        r.findings.some(f => f.severity === filterSeverity)
      );
    }
    
    return filtered;
  };

  const sortReviewers = (insights: ReviewerInsight[]): ReviewerInsight[] => {
    return [...insights].sort((a, b) => {
      switch (sortBy) {
        case 'severity':
          const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
          const aSeverity = Math.min(...a.findings.map(f => severityOrder[f.severity]));
          const bSeverity = Math.min(...b.findings.map(f => severityOrder[f.severity]));
          return aSeverity - bSeverity;
        case 'findings':
          return b.findings.length - a.findings.length;
        case 'confidence':
          return b.confidence - a.confidence;
        default:
          return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      }
    });
  };

  const getChallengesForFinding = (findingId: string): CompetingReview[] => {
    if (!selectedReview) return [];
    return selectedReview.competingReviews.filter(c => c.targetFindingId === findingId);
  };

  const handleVoteChallenge = async (challengeId: string, vote: number) => {
    try {
      await fetch(`/api/challenges/${challengeId}/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vote })
      });
      fetchReviews();
    } catch (error) {
      console.error('Failed to vote on challenge:', error);
    }
  };

  const handleResolveChallenge = async (challengeId: string, resolution: string) => {
    try {
      await fetch(`/api/challenges/${challengeId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution })
      });
      fetchReviews();
    } catch (error) {
      console.error('Failed to resolve challenge:', error);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p>Loading review data...</p>
      </div>
    );
  }

  return (
    <div className="review-dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>CodeForge Review Dashboard</h1>
          <p className="subtitle">Multi-Agent Adversarial Code Review System</p>
        </div>
        <div className="header-actions">
          <button className="btn-refresh" onClick={fetchReviews}>
            ↻ Refresh
          </button>
        </div>
      </header>

      <div className="dashboard-layout">
        <aside className="review-list">
          <div className="review-list-header">
            <h2>Recent Reviews</h2>
            <span className="review-count">{reviews.length}</span>
          </div>
          <div className="review-items">
            {reviews.map(review => (
              <div
                key={review.id}
                className={`review-item ${selectedReview?.id === review.id ? 'active' : ''}`}
                onClick={() => setSelectedReview(review)}
              >
                <div className="review-item-header">
                  <span className="pr-number">#{review.prNumber}</span>
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(review.overallStatus) }}
                  >
                    {review.overallStatus.replace('_', ' ')}
                  </span>
                </div>
                <h3 className="pr-title">{review.prTitle}</h3>
                <div className="review-item-meta">
                  <span className="author">{review.author}</span>
                  <span className="timestamp">{new Date(review.timestamp).toLocaleString()}</span>
                </div>
                <div className="review-item-stats">
                  <span className="stat">
                    <span className="stat-value">{review.metrics.totalFindings}</span>
                    <span className="stat-label">findings</span>
                  </span>
                  <span className="stat">
                    <span className="stat-value">{review.reviewerInsights.length}</span>
                    <span className="stat-label">reviewers</span>
                  </span>
                  <span className="stat">
                    <span className="stat-value">{review.competingReviews.length}</span>
                    <span className="stat-label">challenges</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </aside>

        <main className="review-details">
          {selectedReview ? (
            <>
              <div className="review-header">
                <div className="review-title-section">
                  <h2>PR #{selectedReview.prNumber}: {selectedReview.prTitle}</h2>
                  <div className="review-meta">
                    <span>By {selectedReview.author}</span>
                    <span>•</span>
                    <span>{new Date(selectedReview.timestamp).toLocaleString()}</span>
                  </div>
                </div>
                <div 
                  className="overall-status"
                  style={{ backgroundColor: getStatusColor(selectedReview.overallStatus) }}
                >
                  {selectedReview.overallStatus.replace('_', ' ').toUpperCase()}
                </div>
              </div>

              <div className="metrics-grid">
                <div className="metric-card">
                  <div className="metric-value">{selectedReview.metrics.totalFindings}</div>
                  <div className="metric-label">Total Findings</div>
                </div>
                <div className="metric-card critical">
                  <div className="metric-value">{selectedReview.metrics.criticalFindings}</div>
                  <div className="metric-label">Critical Issues</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">{selectedReview.metrics.challengedFindings}</div>
                  <div className="metric-label">Challenged</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">{selectedReview.metrics.reviewerConsensus}%</div>
                  <div className="metric-label">Consensus</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">{selectedReview.metrics.codeQualityScore}/100</div>
                  <div className="metric-label">Quality Score</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">{selectedReview.metrics.estimatedFixTime}</div>
                  <div className="metric-label">Est. Fix Time</div>
                </div>
              </div>

              <div className="filters-bar">
                <div className="filter-group">
                  <label>Reviewer Type:</label>
                  <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
                    <option value="all">All Types</option>
                    <option value="correctness">Correctness</option>
                    <option value="security">Security</option>
                    <option value="performance">Performance</option>
                    <option value="style">Style</option>
                  </select>
                </div>
                <div className="filter-group">
                  <label>Severity:</label>
                  <select value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)}>
                    <option value="all">All Severities</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                    <option value="info">Info</option>
                  </select>
                </div>
                <div className="filter-group">
                  <label>Sort By:</label>
                  <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                    <option value="timestamp">Latest</option>
                    <option value="severity">Severity</option>
                    <option value="findings">Finding Count</option>
                    <option value="confidence">Confidence</option>
                  </select>
                </div>
                <div className="filter-group">
                  <label className="toggle-label">
                    <input
                      type="checkbox"
                      checked={showCompeting}
                      onChange={(e) => setShowCompeting(e.target.checked)}
                    />
                    Show Competing Reviews
                  </label>
                </div>
              </div>

              <div className="reviewer-insights">
                {sortReviewers(filterReviewers(selectedReview.reviewerInsights)).map(insight => (
                  <div key={insight.reviewerId} className="reviewer-card">
                    <div className="reviewer-header">
                      <div className="reviewer-info">
                        <span className="reviewer-icon">{getReviewerTypeIcon(insight.reviewerType)}</span>
                        <div>
                          <h3>{insight.reviewerName}</h3>
                          <span className="reviewer-type">{insight.reviewerType}</span>
                        </div>
                      </div>
                      <div className="reviewer-status">
                        <span 
                          className="status-badge"
                          style={{ backgroundColor: getStatusColor(insight.status) }}
                        >
                          {insight.status.replace('_', ' ')}
                        </span>
                        <span className="confidence-badge">
                          {Math.round(insight.confidence * 100)}% confidence
                        </span>
                      </div>
                    </div>

                    <div className="findings-list">
                      {insight.findings.map(finding => (
                        <div key={finding.id} className="finding-card">
                          <div 
                            className="