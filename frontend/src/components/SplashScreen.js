import React, { useEffect, useRef, useState } from 'react';
import logo from '../assets/portfolio.svg';

const SplashScreen = ({ onFinish }) => {
  const overlayRef = useRef(null);
  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setFadeOut(true);  // Start fade & slide

      setTimeout(() => {
        onFinish(); // Remove the splash screen after animation
      }, 1000);
    }, 2000); // 2 seconds before animation starts

    return () => clearTimeout(timer);
  }, [onFinish]);

  return (
    <div
      ref={overlayRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'white',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
        transition: 'transform 1s ease-in-out, opacity 1s ease-in-out',
        transform: fadeOut ? 'translateY(-100%)' : 'translateY(0)',
        opacity: fadeOut ? 0 : 1,
      }}
    >
      <img
        src={logo}
        alt="Logo"
        style={{
          width: '350px',
          height: 'auto',
          transition: 'transform 0.5s ease-in-out',
        }}
      />
    </div>
  );
};

export default SplashScreen;
