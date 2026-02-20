import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authService } from '../services/authService';

const RegisterPage = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    setLoading(true);

    try {
      const result = await authService.register(username, password, email, name);
      if (result.success) {
        setSuccess(true);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('注册失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <div style={styles.successIcon}>
            <svg viewBox="0 0 24 24" fill="none" style={{ width: 48, height: 48 }}>
              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" fill="currentColor"/>
            </svg>
          </div>
          <h2 style={styles.title}>注册成功</h2>
          <p style={styles.successText}>您的注册申请已提交，请等待管理员审核。</p>
          <button onClick={() => navigate('/login')} style={styles.button}>
            返回登录
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.iconWrapper}>
          <svg style={styles.icon} viewBox="0 0 24 24" fill="none">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" fill="currentColor"/>
          </svg>
        </div>
        <h1 style={styles.title}>创建账户</h1>
        <p style={styles.subtitle}>注册以使用 Menusifu设备管理平台</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label style={styles.label}>用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={styles.input}
              placeholder="请输入用户名"
              required
              minLength={3}
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>姓名 *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={styles.input}
              placeholder="请输入真实姓名"
              required
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={styles.input}
              placeholder="请输入邮箱地址（选填）"
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
              placeholder="请输入密码（至少6位）"
              required
              minLength={6}
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>确认密码</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              style={styles.input}
              placeholder="请再次输入密码"
              required
            />
          </div>

          {error && <div style={styles.error}>{error}</div>}

          <button type="submit" style={{
            ...styles.button,
            ...(loading ? styles.buttonLoading : {})
          }} disabled={loading}>
            {loading ? '注册中...' : '注册'}
          </button>
        </form>

        <div style={styles.footer}>
          已有账户？
          <Link to="/login" style={styles.link}>立即登录</Link>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    padding: '16px',
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '16px',
    padding: '32px 28px',
    width: '100%',
    maxWidth: '360px',
    boxShadow: '0 16px 32px -8px rgba(0, 0, 0, 0.2)',
  },
  iconWrapper: {
    width: '48px',
    height: '48px',
    borderRadius: '12px',
    background: 'linear-gradient(135deg, #34C759 0%, #30D158 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px',
  },
  icon: {
    width: '24px',
    height: '24px',
    color: 'white',
  },
  successIcon: {
    width: '56px',
    height: '56px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #34C759 0%, #30D158 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px',
    color: 'white',
  },
  title: {
    fontSize: '22px',
    fontWeight: '600',
    textAlign: 'center',
    color: '#1D1D1F',
    marginBottom: '4px',
    letterSpacing: '-0.01em',
  },
  subtitle: {
    fontSize: '13px',
    textAlign: 'center',
    color: '#86868B',
    marginBottom: '24px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#1D1D1F',
  },
  input: {
    padding: '10px 12px',
    border: '1px solid #D1D1D6',
    borderRadius: '8px',
    fontSize: '14px',
    transition: 'all 0.15s ease',
    outline: 'none',
  },
  button: {
    padding: '12px',
    background: 'linear-gradient(135deg, #34C759 0%, #30D158 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    marginTop: '4px',
  },
  buttonLoading: {
    opacity: '0.7',
    cursor: 'not-allowed',
  },
  error: {
    padding: '10px 12px',
    backgroundColor: '#FFF2F0',
    border: '1px solid #FFCCC7',
    borderRadius: '8px',
    color: '#FF4D4F',
    fontSize: '13px',
    textAlign: 'center',
  },
  successText: {
    textAlign: 'center',
    color: '#34C759',
    fontSize: '14px',
    marginBottom: '16px',
    lineHeight: '1.5',
  },
  footer: {
    textAlign: 'center',
    marginTop: '16px',
    fontSize: '13px',
    color: '#86868B',
  },
  link: {
    color: '#007AFF',
    textDecoration: 'none',
    fontWeight: '500',
    marginLeft: '3px',
  },
};

export default RegisterPage;
