import React from 'react';
import logo from '../assets/portfolio.svg';

const TopBar = ({ activeView, setActiveView }) => {
  const tabs = ['Dashboard', 'Matches', 'Insights', 'Settings'];

  return (
    <div style={styles.topBar}>
      <div style={styles.logoContainer}>
        <img src={logo} alt="Portfol.io Logo" style={styles.logo} />
      </div>
      <div style={styles.nav}>
        {tabs.map((tab) => {
          const isActive = activeView === tab;
          return (
            <button
              key={tab}
              onClick={() => setActiveView(tab)}
              style={{
                ...styles.tab,
                ...(isActive ? styles.activeTab : styles.inactiveTab),
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.color = '#a020f0';
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.color = '#003366';
              }}
            >
              {tab}
            </button>
          );
        })}
      </div>
    </div>
  );
};

const styles = {
  topBar: {
    position: 'sticky',
    top: 0,
    zIndex: 999,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 30px',
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
    backdropFilter: 'blur(10px)',
    borderBottom: '1px solid rgba(0,0,0,0.1)',
    boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
  },
  logoContainer: {
    flexShrink: 0,
  },
  logo: {
    height: '70px',
    width: 'auto',
  },
  nav: {
    display: 'flex',
    gap: '16px',
  },
  tab: {
    padding: '10px 20px',
    fontSize: '16px',
    fontWeight: 'bold',
    backgroundColor: 'transparent',
    borderRadius: '20px',
    cursor: 'pointer',
    transition: 'all 0.3s ease-in-out',
  },
  activeTab: {
    border: '2px solid #a020f0', // purple
    boxShadow: '0 2px 8px rgba(160, 32, 240, 0.3)',
    color: '#a020f0',
    backgroundColor: '#f9f4fe',
  },
  inactiveTab: {
    border: 'none',
    color: '#003366',
  },
};

export default TopBar;
