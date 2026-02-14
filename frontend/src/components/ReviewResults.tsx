import React, { useState, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  LinearProgress,
  Tabs,
  Tab,
  Paper,
  List,
  ListItem,
  ListItemText,
  Divider,
  IconButton,
  Tooltip,
  Badge,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Code as CodeIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Style as StyleIcon,
  BugReport as BugReportIcon,
  TrendingUp as TrendingUpIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
} from '@mui/icons-material';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';

interface Finding {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  category: string;
  message: string;
  file: string;
  line: number;
  code?: string;
  suggestion?: string;
  confidence: number;
}

interface AgentReview {
  agentName: string;
  agentType: 'correctness' | 'security' | 'performance' | 'style' | 'bug_hunter';
  timestamp: string;
  overallScore: number;
  findings: Finding[];
  summary: string;
  recommendations: string[];
  challenged?: boolean;
  challengedBy?: string;
}

interface ReviewResultsData {
  prNumber: number;
  prTitle: string;
  author: string;
  timestamp: string;
  overallStatus: 'approved' | 'needs_changes' | 'rejected';
  agentReviews: AgentReview[];
  consensus: {
    approved: number;
    needsChanges: number;
    rejected: number;
  };
  metrics: {
    totalFindings: number;
    criticalIssues: number;
    securityIssues: number;
    performanceIssues: number;
    styleIssues: number;
  };
}

interface ReviewResultsProps {
  data: ReviewResultsData;
}

const SEVERITY_COLORS = {
  critical: '#d32f2f',
  high: '#f57c00',
  medium: '#fbc02d',
  low: '#388e3c',
  info: '#1976d2',
};

const AGENT_TYPE_ICONS = {
  correctness: <CodeIcon />,
  security: <SecurityIcon />,
  performance: <SpeedIcon />,
  style: <StyleIcon />,
  bug_hunter: <BugReportIcon />,
};

const AGENT_TYPE_COLORS = {
  correctness: '#2196f3',
  security: '#f44336',
  performance: '#ff9800',
  style: '#9c27b0',
  bug_hunter: '#4caf50',
};

export const ReviewResults: React.FC<ReviewResultsProps> = ({ data }) => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [expandedAgent, setExpandedAgent] = useState<string | false>(false);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setSelectedTab(newValue);
  };

  const handleAccordionChange = (panel: string) => (
    event: React.SyntheticEvent,
    isExpanded: boolean
  ) => {
    setExpandedAgent(isExpanded ? panel : false);
  };

  const severityDistribution = useMemo(() => {
    const distribution = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      info: 0,
    };

    data.agentReviews.forEach((review) => {
      review.findings.forEach((finding) => {
        distribution[finding.severity]++;
      });
    });

    return Object.entries(distribution).map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value,
      color: SEVERITY_COLORS[name as keyof typeof SEVERITY_COLORS],
    }));
  }, [data]);

  const agentScores = useMemo(() => {
    return data.agentReviews.map((review) => ({
      name: review.agentName,
      score: review.overallScore,
      type: review.agentType,
    }));
  }, [data]);

  const categoryBreakdown = useMemo(() => {
    const categories: { [key: string]: number } = {};

    data.agentReviews.forEach((review) => {
      review.findings.forEach((finding) => {
        categories[finding.category] = (categories[finding.category] || 0) + 1;
      });
    });

    return Object.entries(categories)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [data]);

  const radarData = useMemo(() => {
    const metrics = {
      Correctness: 0,
      Security: 0,
      Performance: 0,
      Style: 0,
      'Bug Resistance': 0,
    };

    data.agentReviews.forEach((review) => {
      switch (review.agentType) {
        case 'correctness':
          metrics.Correctness = review.overallScore;
          break;
        case 'security':
          metrics.Security = review.overallScore;
          break;
        case 'performance':
          metrics.Performance = review.overallScore;
          break;
        case 'style':
          metrics.Style = review.overallScore;
          break;
        case 'bug_hunter':
          metrics['Bug Resistance'] = review.overallScore;
          break;
      }
    });

    return Object.entries(metrics).map(([subject, value]) => ({
      subject,
      value,
      fullMark: 100,
    }));
  }, [data]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircleIcon sx={{ color: '#4caf50' }} />;
      case 'needs_changes':
        return <WarningIcon sx={{ color: '#ff9800' }} />;
      case 'rejected':
        return <ErrorIcon sx={{ color: '#f44336' }} />;
      default:
        return <InfoIcon />;
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <ErrorIcon fontSize="small" />;
      case 'medium':
        return <WarningIcon fontSize="small" />;
      case 'low':
      case 'info':
        return <InfoIcon fontSize="small" />;
      default:
        return null;
    }
  };

  const renderOverview = () => (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Card elevation={3}>
          <CardContent>
            <Box display="flex" alignItems="center" gap={2} mb={2}>
              {getStatusIcon(data.overallStatus)}
              <Typography variant="h5">
                PR #{data.prNumber}: {data.prTitle}
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Author: {data.author} | Reviewed: {new Date(data.timestamp).toLocaleString()}
            </Typography>
            <Box mt={2}>
              <Chip
                label={data.overallStatus.replace('_', ' ').toUpperCase()}
                color={
                  data.overallStatus === 'approved'
                    ? 'success'
                    : data.overallStatus === 'needs_changes'
                    ? 'warning'
                    : 'error'
                }
                sx={{ mr: 1 }}
              />
              <Chip
                label={`${data.agentReviews.length} Agent Reviews`}
                variant="outlined"
                sx={{ mr: 1 }}
              />
              <Chip
                label={`${data.metrics.totalFindings} Total Findings`}
                variant="outlined"
              />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={4}>
        <Card elevation={2}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Review Consensus
            </Typography>
            <Box mt={2}>
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">Approved</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {data.consensus.approved}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={(data.consensus.approved / data.agentReviews.length) * 100}
                sx={{ height: 8, borderRadius: 1, mb: 2, backgroundColor: '#e0e0e0' }}
                color="success"
              />

              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">Needs Changes</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {data.consensus.needsChanges}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={(data.consensus.needsChanges / data.agentReviews.length) * 100}
                sx={{ height: 8, borderRadius: 1, mb: 2, backgroundColor: '#e0e0e0' }}
                color="warning"
              />

              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2">Rejected</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {data.consensus.rejected}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={(data.consensus.rejected / data.agentReviews.length) * 100}
                sx={{ height: 8, borderRadius: 1, backgroundColor: '#e0e0e0' }}
                color="error"
              />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={4}>
        <Card elevation={2}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Severity Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={severityDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => (value > 0 ? `${name}: ${value}` : '')}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {severityDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={4}>
        <Card elevation={2}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Key Metrics
            </Typography>
            <List dense>
              <ListItem>
                <ListItemText
                  primary="Critical Issues"
                  secondary={data.metrics.criticalIssues}
                />
                <Badge badgeContent={data.metrics.criticalIssues} color="error" />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText
                  primary="Security Issues"
                  secondary={data.metrics.securityIssues}
                />
                <Badge badgeContent={data.metrics.securityIssues} color="warning" />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText
                  primary="Performance Issues"
                  secondary={data.metrics.performanceIssues}
                />
                <Badge badgeContent={data.metrics.performanceIssues} color="info" />
              </ListItem>
              <Divider />
              <ListItem>
                <ListItemText
                  primary="Style Issues"
                  secondary={data.metrics.styleIssues}
                />
                <Badge badgeContent={data.metrics.styleIssues} color="default" />
              </ListItem>
            </List>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6}>
        <Card elevation={2}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Agent Scores
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={agentScores}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                <YAxis domain={[0, 100]} />
                <RechartsTooltip />
                <Legend />
                <Bar dataKey="score" fill="#8884d8" name="Score">
                  {agentScores.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={AGENT_TYPE_COLORS[entry.type]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6}>
        <Card elevation={2}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Quality Radar
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" />
                <PolarRadiusAxis domain={[0, 100]} />
                <Radar
                  name="Score"
                  dataKey="value"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.6}
                />
                <RechartsTooltip />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12}>
        <Card elevation={2}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Issue Categories
            </Typography>