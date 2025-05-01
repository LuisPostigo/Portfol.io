import React, { useState } from 'react';
import FileDrop from './components/FileDrop';
import axios from 'axios';
import SplashScreen from './components/SplashScreen';
import TopBar from './components/TopBar';
import Insights from './components/Insights';
import Matches from './components/Matches';  // <-- ✅ You forgot to show Matches before!

import './styles/collageBackground.css';
import './App.css';

function App() {
  const [resumes, setResumes] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [message, setMessage] = useState('');
  const [showSplash, setShowSplash] = useState(true);
  const [activeView, setActiveView] = useState('Dashboard');

  const uploadFiles = async () => {
    const formData = new FormData();
    resumes.forEach((file) => formData.append('resumes', file));
    jobs.forEach((file) => formData.append('jobs', file));

    try {
      const response = await axios.post('http://localhost:8000/process', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setMessage(response.data.message || 'Files processed successfully!');
    } catch (error) {
      console.error(error);
      setMessage('Error processing files.');
    }
  };

  return (
    <>
      {showSplash && <SplashScreen onFinish={() => setShowSplash(false)} />}
      {!showSplash && (
        <div style={{ fontFamily: 'Arial, sans-serif', height: '100vh', overflow: 'hidden' }}>
          <TopBar activeView={activeView} setActiveView={setActiveView} />

          {activeView === 'Dashboard' && (
            <div className="collage-background" style={styles.outerContainer}>
              <div style={styles.innerBox}>
                <h1 style={styles.hello}>
                  <span style={styles.helloStroke}>Let's get Started!</span>
                </h1>

                <FileDrop label="Drop Resumes Here" onFilesSelected={(files) => setResumes(files)} />
                <FileDrop label="Drop Job Postings Here" onFilesSelected={(files) => setJobs(files)} />

                <button
                  onClick={uploadFiles}
                  style={{ ...styles.button, marginTop: '30px' }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = '0 6px 18px rgba(160, 32, 240, 0.4)';
                    e.currentTarget.style.backgroundColor = '#f0e6fc';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(160, 32, 240, 0.3)';
                    e.currentTarget.style.backgroundColor = '#f9f4fe';
                  }}
                >
                  Process Files
                </button>
                <p style={{ textAlign: 'center', marginTop: '20px', color: '#00796b' }}>{message}</p>
              </div>
            </div>
          )}

          {activeView === 'Insights' && <Insights />} 
          {activeView === 'Matches' && <Matches />}   {/* ✅ You needed to add this */}
        </div>
      )}
    </>
  );
}

const styles = {
  button: {
    width: '100%',
    padding: '15px',
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#a020f0',
    backgroundColor: '#f9f4fe',
    border: '2px solid #a020f0',
    borderRadius: '25px',
    boxShadow: '0 4px 12px rgba(160, 32, 240, 0.3)',
    cursor: 'pointer',
    transition: 'all 0.3s ease-in-out',
  },
  outerContainer: {
    backgroundColor: '#f2f2f2',
    minHeight: 'calc(100vh - 0px)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '0px',
  },
  innerBox: {
    backgroundColor: 'white',
    padding: '50px',
    borderRadius: '20px',
    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.1)',
    maxWidth: '700px',
    width: '100%',
    minHeight: '500px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
  },
  helloStroke: {
    display: 'inline-block',
    position: 'relative',
    color: '#000',
    fontFamily: '"Rock Salt", cursive',
    fontSize: 'inherit',
    WebkitTextStroke: 'none',
    overflow: 'visible',
    background: 'none',
    backgroundSize: 'unset',
    backgroundClip: 'unset',
    WebkitBackgroundClip: 'unset',
    animation: 'none',
  },
  hello: {
    fontFamily: '"Rock Salt"',
    fontSize: '25px',
    letterSpacing: '2px',
    margin: '0 0 10px 0',
    textShadow: '2px 2px rgba(0, 0, 0, 0.1)',
    alignSelf: 'flex-start',
    paddingLeft: '15px',
  },
};

export default App;
