import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Menu,
  MenuItem
} from '@mui/material';
import {
  LocalLibrary as LibraryIcon,
  AccountCircle,
  Menu as MenuIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Navbar = () => {
  const navigate = useNavigate();
  const { user, logout, isAuthenticated } = useAuth();
  const [anchorEl, setAnchorEl] = React.useState(null);
  const [mobileMenuAnchor, setMobileMenuAnchor] = React.useState(null);

  const handleProfileMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMobileMenu = (event) => {
    setMobileMenuAnchor(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
    setMobileMenuAnchor(null);
  };

  const handleLogout = () => {
    logout();
    handleClose();
    navigate('/');
  };

  return (
    <AppBar position="static">
      <Toolbar>
        <IconButton
          size="large"
          edge="start"
          color="inherit"
          aria-label="logo"
          onClick={() => navigate('/')}
          sx={{ mr: 2 }}
        >
          <LibraryIcon />
        </IconButton>

        <Typography
          variant="h6"
          component="div"
          sx={{ flexGrow: 1, cursor: 'pointer' }}
          onClick={() => navigate('/')}
        >
          Biblioteka Miejska
        </Typography>

        <Box sx={{ display: { xs: 'none', md: 'flex' } }}>
          <Button color="inherit" onClick={() => navigate('/')}>
            Strona Główna
          </Button>
          <Button color="inherit" onClick={() => navigate('/books')}>
            Katalog Książek
          </Button>

          {isAuthenticated ? (
            <>
              <Button color="inherit" onClick={() => navigate('/my-loans')}>
                Moje Wypożyczenia
              </Button>
              {(user?.role === 'librarian' || user?.role === 'admin') && (
                <Button color="inherit" onClick={() => navigate('/admin')}>
                  Panel Admina
                </Button>
              )}
              <IconButton
                size="large"
                color="inherit"
                onClick={handleProfileMenu}
              >
                <AccountCircle />
              </IconButton>
              <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleClose}
              >
                <MenuItem onClick={() => { navigate('/profile'); handleClose(); }}>
                  Profil
                </MenuItem>
                <MenuItem onClick={handleLogout}>Wyloguj</MenuItem>
              </Menu>
            </>
          ) : (
            <>
              <Button color="inherit" onClick={() => navigate('/login')}>
                Zaloguj
              </Button>
              <Button color="inherit" onClick={() => navigate('/register')}>
                Zarejestruj
              </Button>
            </>
          )}
        </Box>

        <Box sx={{ display: { xs: 'flex', md: 'none' } }}>
          <IconButton
            size="large"
            color="inherit"
            onClick={handleMobileMenu}
          >
            <MenuIcon />
          </IconButton>
          <Menu
            anchorEl={mobileMenuAnchor}
            open={Boolean(mobileMenuAnchor)}
            onClose={handleClose}
          >
            <MenuItem onClick={() => { navigate('/'); handleClose(); }}>
              Strona Główna
            </MenuItem>
            <MenuItem onClick={() => { navigate('/books'); handleClose(); }}>
              Katalog Książek
            </MenuItem>
            {isAuthenticated ? (
              <>
                <MenuItem onClick={() => { navigate('/my-loans'); handleClose(); }}>
                  Moje Wypożyczenia
                </MenuItem>
                <MenuItem onClick={() => { navigate('/profile'); handleClose(); }}>
                  Profil
                </MenuItem>
                <MenuItem onClick={handleLogout}>Wyloguj</MenuItem>
              </>
            ) : (
              <>
                <MenuItem onClick={() => { navigate('/login'); handleClose(); }}>
                  Zaloguj
                </MenuItem>
                <MenuItem onClick={() => { navigate('/register'); handleClose(); }}>
                  Zarejestruj
                </MenuItem>
              </>
            )}
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
