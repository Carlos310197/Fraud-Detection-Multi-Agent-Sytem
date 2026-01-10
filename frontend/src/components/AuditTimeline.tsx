import React, { useState } from 'react';
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  TimelineOppositeContent,
} from '@mui/lab';
import { 
  Paper, 
  Typography, 
  Chip, 
  Box, 
  Collapse, 
  IconButton, 
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stack
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import ErrorIcon from '@mui/icons-material/Error';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import type { AuditEvent } from '../types';

interface AuditTimelineProps {
  events: AuditEvent[];
}

interface GroupedEvents {
  run_id: string;
  events: AuditEvent[];
  first_ts: string;
  total_duration_ms: number;
}

const getAgentIcon = (agent: string) => {
  if (agent === 'HITL') {
    return <PersonIcon />;
  }
  if (agent.includes('error')) {
    return <ErrorIcon />;
  }
  return <SmartToyIcon />;
};

const getAgentColor = (agent: string): 'primary' | 'secondary' | 'error' | 'success' | 'warning' => {
  if (agent === 'HITL') return 'secondary';
  if (agent.includes('error')) return 'error';
  if (agent === 'Arbiter') return 'success';
  if (agent.includes('Debate')) return 'warning';
  return 'primary';
};

const formatTimestamp = (ts: string): string => {
  try {
    return new Date(ts).toLocaleString('es-PE', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return ts;
  }
};

const formatDuration = (ms: number): string => {
  if (ms < 1000) {
    return `${ms.toFixed(0)}ms`;
  }
  return `${(ms / 1000).toFixed(2)}s`;
};

const extractCitations = (outputJson: Record<string, unknown>): { internal: number; external: number } => {
  const internal = (outputJson.citations_internal as any[])?.length || 0;
  const external = (outputJson.citations_external as any[])?.length || 0;
  return { internal, external };
};

export const AuditTimeline: React.FC<AuditTimelineProps> = ({ events }) => {
  const [expandedSeq, setExpandedSeq] = useState<number | null>(null);

  if (events.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No hay eventos de auditoría.
      </Typography>
    );
  }

  // Group events by run_id
  const groupedByRun: Map<string, GroupedEvents> = new Map();
  
  events.forEach(event => {
    if (!groupedByRun.has(event.run_id)) {
      groupedByRun.set(event.run_id, {
        run_id: event.run_id,
        events: [],
        first_ts: event.ts,
        total_duration_ms: 0,
      });
    }
    const group = groupedByRun.get(event.run_id)!;
    group.events.push(event);
    group.total_duration_ms += event.duration_ms;
    // Update first_ts if this event is earlier
    if (new Date(event.ts) < new Date(group.first_ts)) {
      group.first_ts = event.ts;
    }
  });

  // Convert to array and sort by first timestamp (newest first)
  const sortedGroups = Array.from(groupedByRun.values()).sort(
    (a, b) => new Date(b.first_ts).getTime() - new Date(a.first_ts).getTime()
  );

  const toggleExpand = (seq: number) => {
    setExpandedSeq(expandedSeq === seq ? null : seq);
  };

  return (
    <Box>
      {sortedGroups.map((group, groupIndex) => {
        const sortedEvents = [...group.events].sort((a, b) => a.seq - b.seq);
        const runLabel = group.run_id === 'hitl-manual' 
          ? 'Resolución Manual HITL' 
          : `Análisis ${sortedGroups.length - groupIndex}`;

        return (
          <Accordion key={group.run_id} defaultExpanded={false} sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                <Chip 
                  label={runLabel} 
                  color="primary" 
                  size="small"
                  variant={groupIndex === 0 ? "filled" : "outlined"}
                />
                <Typography variant="caption" color="text.secondary">
                  {formatTimestamp(group.first_ts)}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, ml: 'auto' }}>
                  <AccessTimeIcon fontSize="small" color="action" />
                  <Typography variant="caption" color="text.secondary">
                    {formatDuration(group.total_duration_ms)}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {sortedEvents.length} pasos
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Timeline position="alternate">
                {sortedEvents.map((event, index) => {
                  const isExpanded = expandedSeq === event.seq;
                  const citations = extractCitations(event.output_json);
                  
                  return (
                    <TimelineItem key={`${event.transaction_id}-${event.seq}`}>
                      <TimelineOppositeContent color="text.secondary" sx={{ flex: 0.3 }}>
                        <Typography variant="caption">{formatTimestamp(event.ts)}</Typography>
                        <Typography variant="caption" display="block" sx={{ color: 'success.main' }}>
                          {formatDuration(event.duration_ms)}
                        </Typography>
                      </TimelineOppositeContent>
                      <TimelineSeparator>
                        <TimelineDot color={getAgentColor(event.agent)}>
                          {getAgentIcon(event.agent)}
                        </TimelineDot>
                        {index < sortedEvents.length - 1 && <TimelineConnector />}
                      </TimelineSeparator>
                      <TimelineContent>
                        <Paper elevation={2} sx={{ p: 1.5 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, flexWrap: 'wrap' }}>
                            <Chip label={event.agent} size="small" color={getAgentColor(event.agent)} />
                            <Typography variant="caption" color="text.secondary">
                              #{event.seq}
                            </Typography>
                            {(citations.internal > 0 || citations.external > 0) && (
                              <Chip 
                                label={`${citations.internal} int, ${citations.external} ext`}
                                size="small" 
                                variant="outlined"
                                color="info"
                              />
                            )}
                            <IconButton size="small" onClick={() => toggleExpand(event.seq)} sx={{ ml: 'auto' }}>
                              {isExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                            </IconButton>
                          </Box>
                          <Typography variant="body2">{event.output_summary}</Typography>
                          <Collapse in={isExpanded}>
                            <Box sx={{ mt: 1, pt: 1, borderTop: 1, borderColor: 'divider' }}>
                              <Typography variant="caption" color="text.secondary" display="block">
                                <strong>Input:</strong> {event.input_summary}
                              </Typography>
                              
                              {/* Show citations if they exist */}
                              {(citations.internal > 0 || citations.external > 0) && (
                                <Box sx={{ mt: 1 }}>
                                  <Typography variant="caption" color="text.secondary" display="block">
                                    <strong>Citaciones:</strong>
                                  </Typography>
                                  {citations.internal > 0 && (
                                    <Stack direction="row" spacing={0.5} sx={{ mt: 0.5, flexWrap: 'wrap', gap: 0.5 }}>
                                      {(event.output_json.citations_internal as any[])?.map((cit: any, idx: number) => (
                                        <Chip 
                                          key={idx}
                                          label={cit.policy_id || 'N/A'}
                                          size="small"
                                          variant="outlined"
                                          color="primary"
                                        />
                                      ))}
                                    </Stack>
                                  )}
                                  {citations.external > 0 && (
                                    <Stack direction="row" spacing={0.5} sx={{ mt: 0.5, flexWrap: 'wrap', gap: 0.5 }}>
                                      {(event.output_json.citations_external as any[])?.map((cit: any, idx: number) => (
                                        <Chip 
                                          key={idx}
                                          label={cit.url ? new URL(cit.url).hostname : 'External'}
                                          size="small"
                                          variant="outlined"
                                          color="secondary"
                                        />
                                      ))}
                                    </Stack>
                                  )}
                                </Box>
                              )}

                              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                                <strong>Output JSON:</strong>
                              </Typography>
                              <Paper sx={{ p: 1, mt: 0.5, bgcolor: 'grey.100', maxHeight: 300, overflow: 'auto' }}>
                                <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.7rem' }}>
                                  {JSON.stringify(event.output_json, null, 2)}
                                </Typography>
                              </Paper>
                            </Box>
                          </Collapse>
                        </Paper>
                      </TimelineContent>
                    </TimelineItem>
                  );
                })}
              </Timeline>
            </AccordionDetails>
          </Accordion>
        );
      })}
    </Box>
  );
};

export default AuditTimeline;
