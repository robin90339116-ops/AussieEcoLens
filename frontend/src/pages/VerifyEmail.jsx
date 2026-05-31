import { Button, Form, Input, Space, Typography, message } from 'antd';
import { CheckCircle2, RefreshCw } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function VerifyEmail() {
  const navigate = useNavigate();
  const location = useLocation();
  const { pendingUsername, verifyEmail, resendCode } = useAuth();
  const email = location.state?.email || pendingUsername;

  const handleSubmit = async (values) => {
    try {
      await verifyEmail({ email: values.email, code: values.code });
      message.success('Email verified');
      navigate('/login');
    } catch (error) {
      message.error(error.message || 'Verification failed');
    }
  };

  const handleResend = async () => {
    try {
      await resendCode(email);
      message.success('Verification code sent');
    } catch (error) {
      message.error(error.message || 'Could not resend code');
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="auth-brand">
          <span className="brand-mark">AE</span>
          <Typography.Title level={1}>Verify email</Typography.Title>
        </div>
        <Form
          layout="vertical"
          onFinish={handleSubmit}
          requiredMark={false}
          initialValues={{ email }}
        >
          <Form.Item
            name="email"
            label="Email"
            rules={[{ required: true, type: 'email', message: 'Enter a valid email' }]}
          >
            <Input size="large" />
          </Form.Item>
          <Form.Item
            name="code"
            label="Verification code"
            rules={[{ required: true, message: 'Enter the code' }]}
          >
            <Input size="large" autoComplete="one-time-code" />
          </Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            block
            icon={<CheckCircle2 size={18} />}
          >
            Verify
          </Button>
        </Form>
        <Space className="auth-footer">
          <Button type="link" icon={<RefreshCw size={16} />} onClick={handleResend}>
            Resend
          </Button>
          <Link to="/login">Back to sign in</Link>
        </Space>
      </section>
    </main>
  );
}

