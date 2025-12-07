import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  CardMedia,
  Grid,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Divider,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  MenuBook,
  CalendarMonth,
  Refresh,
  CheckCircle,
  Warning,
  History,
  LocalLibrary,
  ArrowForward,
  Autorenew
} from '@mui/icons-material';
import { loansAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const MyLoans = () => {
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading } = useAuth();

  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tabValue, setTabValue] = useState(0); 

  const [returnDialog, setReturnDialog] = useState({ open: false, loan: null });
  const [returning, setReturning] = useState(false);

  const [renewDialog, setRenewDialog] = useState({ open: false, loan: null });
  const [renewing, setRenewing] = useState(false);

  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/login', { state: { from: '/my-loans' } });
    }
  }, [isAuthenticated, authLoading, navigate]);

  const fetchLoans = async () => {
    try {
      setLoading(true);
      const response = await loansAPI.getMine();
      setLoans(response.data);
      setError('');
    } catch (err) {
      console.error('Error fetching loans:', err);
      setError('Nie udało się pobrać wypożyczeń');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchLoans();
    }
  }, [isAuthenticated]);

  const activeLoans = loans.filter(loan => loan.status === 'active');
  const historyLoans = loans.filter(loan => loan.status !== 'active');

  const getDaysRemaining = (dueDate) => {
    const now = new Date();
    const due = new Date(dueDate);
    const diffTime = due - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('pl-PL', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const handleReturn = async () => {
    if (!returnDialog.loan) return;

    try {
      setReturning(true);
      await loansAPI.return(returnDialog.loan._id);
      
      setSnackbar({
        open: true,
        message: 'Książka została zwrócona!',
        severity: 'success'
      });
      
      setReturnDialog({ open: false, loan: null });
      fetchLoans();
    } catch (err) {
      console.error('Error returning book:', err);
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Nie udało się zwrócić książki',
        severity: 'error'
      });
    } finally {
      setReturning(false);
    }
  };

  const handleRenew = async () => {
    if (!renewDialog.loan) return;

    try {
      setRenewing(true);
      const response = await loansAPI.renew(renewDialog.loan._id);
      
      setSnackbar({
        open: true,
        message: `Wypożyczenie przedłużone! Nowy termin: ${formatDate(response.data.new_due_date)}`,
        severity: 'success'
      });
      
      setRenewDialog({ open: false, loan: null });
      fetchLoans(); 
    } catch (err) {
      console.error('Error renewing loan:', err);
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Nie udało się przedłużyć wypożyczenia',
        severity: 'error'
      });
    } finally {
      setRenewing(false);
    }
  };

  const LoanCard = ({ loan, showActions = true }) => {
    const daysRemaining = getDaysRemaining(loan.due_date);
    const isOverdue = loan.status === 'active' && daysRemaining < 0;
    const isAlmostDue = loan.status === 'active' && daysRemaining >= 0 && daysRemaining <= 3;

    return (
      <Card 
        sx={{ 
          mb: 2, 
          border: isOverdue ? '2px solid #f44336' : isAlmostDue ? '2px solid #ff9800' : 'none',
          transition: 'all 0.2s',
          '&:hover': { boxShadow: 4 }
        }}
      >
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={3} md={2}>
              <CardMedia
                component="div"
                sx={{
                  height: 150,
                  backgroundImage: loan.book_image
                    ? `url(${loan.book_image})`
                    : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                  borderRadius: 1,
                  cursor: 'pointer'
                }}
                onClick={() => navigate(`/books/${loan.book_id}`)}
              />
            </Grid>

            <Grid item xs={12} sm={9} md={10}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <Box sx={{ flex: 1, minWidth: 200 }}>
                  <Typography 
                    variant="h6" 
                    sx={{ 
                      cursor: 'pointer',
                      '&:hover': { color: 'primary.main' }
                    }}
                    onClick={() => navigate(`/books/${loan.book_id}`)}
                  >
                    {loan.book_title || 'Nieznany tytuł'}
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {loan.book_author || ''}
                  </Typography>

                  <Box sx={{ mt: 1, mb: 1 }}>
                    {loan.status === 'active' ? (
                      isOverdue ? (
                        <Chip 
                          icon={<Warning />} 
                          label={`Przeterminowane o ${Math.abs(daysRemaining)} dni`} 
                          color="error" 
                          size="small" 
                        />
                      ) : isAlmostDue ? (
                        <Chip 
                          icon={<Warning />} 
                          label={`Pozostało ${daysRemaining} dni`} 
                          color="warning" 
                          size="small" 
                        />
                      ) : (
                        <Chip 
                          icon={<CheckCircle />} 
                          label={`Pozostało ${daysRemaining} dni`} 
                          color="success" 
                          size="small" 
                        />
                      )
                    ) : (
                      <Chip 
                        icon={<History />} 
                        label="Zwrócona" 
                        color="default" 
                        size="small" 
                      />
                    )}
                  </Box>

                  <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mt: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <CalendarMonth sx={{ fontSize: 16, mr: 0.5, color: 'text.secondary' }} />
                      <Typography variant="caption" color="text.secondary">
                        Wypożyczono: {formatDate(loan.loan_date)}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <CalendarMonth sx={{ fontSize: 16, mr: 0.5, color: 'text.secondary' }} />
                      <Typography variant="caption" color="text.secondary">
                        Termin zwrotu: {formatDate(loan.due_date)}
                      </Typography>
                    </Box>
                    {loan.return_date && (
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <CheckCircle sx={{ fontSize: 16, mr: 0.5, color: 'success.main' }} />
                        <Typography variant="caption" color="text.secondary">
                          Zwrócono: {formatDate(loan.return_date)}
                        </Typography>
                      </Box>
                    )}
                  </Box>

                  {loan.status === 'active' && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                      Przedłużenia: {loan.renewal_count || 0} / {loan.max_renewals || 2}
                    </Typography>
                  )}
                </Box>

                {showActions && loan.status === 'active' && (
                  <Box sx={{ display: 'flex', gap: 1, mt: { xs: 2, sm: 0 } }}>
                    <Tooltip title="Przedłuż wypożyczenie">
                      <span>
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={<Autorenew />}
                          disabled={(loan.renewal_count || 0) >= (loan.max_renewals || 2)}
                          onClick={() => setRenewDialog({ open: true, loan })}
                        >
                          Przedłuż
                        </Button>
                      </span>
                    </Tooltip>
                    <Button
                      variant="contained"
                      size="small"
                      color="primary"
                      onClick={() => setReturnDialog({ open: true, loan })}
                    >
                      Zwróć
                    </Button>
                  </Box>
                )}
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    );
  };

  if (authLoading || loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
            <LocalLibrary sx={{ mr: 1, fontSize: 40 }} />
            Moje wypożyczenia
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {activeLoans.length} aktywnych wypożyczeń
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={fetchLoans}
        >
          Odśwież
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={(e, newValue) => setTabValue(newValue)}
          indicatorColor="primary"
          textColor="primary"
        >
          <Tab 
            label={`Aktywne (${activeLoans.length})`} 
            icon={<MenuBook />} 
            iconPosition="start" 
          />
          <Tab 
            label={`Historia (${historyLoans.length})`} 
            icon={<History />} 
            iconPosition="start" 
          />
        </Tabs>
      </Paper>

      {tabValue === 0 ? (
        activeLoans.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <MenuBook sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Nie masz żadnych aktywnych wypożyczeń
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Przejdź do katalogu i wypożycz swoją pierwszą książkę!
            </Typography>
            <Button
              variant="contained"
              endIcon={<ArrowForward />}
              onClick={() => navigate('/books')}
            >
              Przeglądaj katalog
            </Button>
          </Paper>
        ) : (
          <Box>
            {activeLoans.some(loan => getDaysRemaining(loan.due_date) < 0) && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <strong>Uwaga!</strong> Masz przeterminowane wypożyczenia. Prosimy o jak najszybszy zwrot.
              </Alert>
            )}
            
            {activeLoans.some(loan => {
              const days = getDaysRemaining(loan.due_date);
              return days >= 0 && days <= 3;
            }) && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Niektóre wypożyczenia zbliżają się do terminu zwrotu.
              </Alert>
            )}

            {activeLoans.map(loan => (
              <LoanCard key={loan._id} loan={loan} />
            ))}
          </Box>
        )
      ) : (
        historyLoans.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <History sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">
              Brak historii wypożyczeń
            </Typography>
          </Paper>
        ) : (
          <Box>
            {historyLoans.map(loan => (
              <LoanCard key={loan._id} loan={loan} showActions={false} />
            ))}
          </Box>
        )
      )}

      <Dialog open={returnDialog.open} onClose={() => setReturnDialog({ open: false, loan: null })}>
        <DialogTitle>Potwierdź zwrot książki</DialogTitle>
        <DialogContent>
          <Typography>
            Czy na pewno chcesz zwrócić książkę "{returnDialog.loan?.book_title}"?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReturnDialog({ open: false, loan: null })}>
            Anuluj
          </Button>
          <Button
            variant="contained"
            onClick={handleReturn}
            disabled={returning}
          >
            {returning ? 'Zwracanie...' : 'Zwróć książkę'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={renewDialog.open} onClose={() => setRenewDialog({ open: false, loan: null })}>
        <DialogTitle>Przedłuż wypożyczenie</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>
            Czy chcesz przedłużyć wypożyczenie książki "{renewDialog.loan?.book_title}"?
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Wypożyczenie zostanie przedłużone o 14 dni.
          </Typography>
          {renewDialog.loan && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Pozostałe przedłużenia: {(renewDialog.loan.max_renewals || 2) - (renewDialog.loan.renewal_count || 0)}
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenewDialog({ open: false, loan: null })}>
            Anuluj
          </Button>
          <Button
            variant="contained"
            onClick={handleRenew}
            disabled={renewing}
          >
            {renewing ? 'Przedłużanie...' : 'Przedłuż'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default MyLoans;