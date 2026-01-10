import React from 'react';
import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  Paper,
  Link,
  Divider,
  Box,
} from '@mui/material';
import PolicyIcon from '@mui/icons-material/Policy';
import PublicIcon from '@mui/icons-material/Public';
import type { CitationInternal, CitationExternal } from '../types';

interface EvidenceListProps {
  citationsInternal: CitationInternal[];
  citationsExternal: CitationExternal[];
}

export const EvidenceList: React.FC<EvidenceListProps> = ({
  citationsInternal,
  citationsExternal,
}) => {
  const hasInternalCitations = citationsInternal && citationsInternal.length > 0;
  const hasExternalCitations = citationsExternal && citationsExternal.length > 0;

  if (!hasInternalCitations && !hasExternalCitations) {
    return (
      <Typography variant="body2" color="text.secondary">
        No se encontraron evidencias.
      </Typography>
    );
  }

  return (
    <Box>
      {hasInternalCitations && (
        <>
          <Typography variant="subtitle2" gutterBottom sx={{ mt: 1 }}>
            Políticas Internas
          </Typography>
          <Paper variant="outlined" sx={{ mb: 2 }}>
            <List dense>
              {citationsInternal.map((citation, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <PolicyIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText
                    primary={`Política ${citation.policy_id}`}
                    secondary={`Versión: ${citation.version} | Chunk: ${citation.chunk_id}`}
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </>
      )}

      {hasExternalCitations && (
        <>
          <Typography variant="subtitle2" gutterBottom>
            Alertas Externas
          </Typography>
          <Paper variant="outlined">
            <List dense>
              {citationsExternal.map((citation, index) => (
                <React.Fragment key={index}>
                  {index > 0 && <Divider />}
                  <ListItem alignItems="flex-start">
                    <ListItemIcon>
                      <PublicIcon color="error" />
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Link href={citation.url} target="_blank" rel="noopener noreferrer">
                          {new URL(citation.url).hostname}
                        </Link>
                      }
                      secondary={citation.summary}
                    />
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          </Paper>
        </>
      )}
    </Box>
  );
};

export default EvidenceList;
