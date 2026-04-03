// src/App.jsx
import React from 'react';
import UsageStats from './components/UsageStats';

function App() {
  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Fidant Usage Dashboard</h1>
      {/* UsageStats component renders bar chart and summary */}
      <UsageStats />
    </div>
  );
}

export default App;