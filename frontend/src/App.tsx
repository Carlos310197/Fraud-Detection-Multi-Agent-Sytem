import { Outlet, Link as RouterLink, useLocation } from 'react-router-dom';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  Container,
  Tabs,
  Tab,
  CssBaseline,
  ThemeProvider,
  createTheme,
} from '@mui/material';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
});

function App() {
  const location = useLocation();
  
  const getCurrentTab = () => {
    if (location.pathname.startsWith('/hitl')) return 1;
    return 0;
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <AppBar position="static" elevation={1}>
          <Toolbar>
            <Box
              component="img"
              src="/app-logo.png"
              alt="App Logo"
              sx={{ height: 40, mr: 2 }}
            />
            <Typography variant="h6" component="div" sx={{ flexGrow: 0, mr: 4 }}>
              Sistema de Detección de Fraude
            </Typography>
            <Tabs
              value={getCurrentTab()}
              textColor="inherit"
              indicatorColor="secondary"
              sx={{ flexGrow: 1 }}
            >
              <Tab
                label="Transacciones"
                component={RouterLink}
                to="/"
              />
              <Tab
                label="Cola HITL"
                component={RouterLink}
                to="/hitl"
              />
            </Tabs>
          </Toolbar>
        </AppBar>
        <Container maxWidth="xl" sx={{ flexGrow: 1, py: 2 }}>
          <Outlet />
        </Container>
        <Box
          component="footer"
          sx={{
            py: 2,
            px: 2,
            mt: 'auto',
            backgroundColor: 'background.paper',
            borderTop: 1,
            borderColor: 'divider',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Sistema Multi-Agente para Detección de Fraude
            </Typography>
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
