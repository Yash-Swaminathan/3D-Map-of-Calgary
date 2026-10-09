import React, { useState } from 'react';
import styled from 'styled-components';
import toast from 'react-hot-toast';
import { apiService } from '../../services/dashboardApi';

const LoginContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: #edf1f2;
`;

const LoginCard = styled.div`
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 40px;
  border-radius: 20px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  text-align: center;
  max-width: 400px;
  width: 90%;
`;

const Title = styled.h1`
  margin: 0 0 30px 0;
  color: #333;
  font-size: 28px;
  font-weight: 600;
`;

const Subtitle = styled.p`
  margin: 0 0 30px 0;
  color: #666;
  font-size: 16px;
  line-height: 1.5;
`;

const InputGroup = styled.div`
  margin-bottom: 20px;
  text-align: left;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 8px;
  color: #333;
  font-weight: 500;
`;

const Input = styled.input`
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e1e1e1;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.3s ease;
  box-sizing: border-box;

  &:focus {
    outline: none;
    border-color: #667eea;
  }

  &:disabled {
    background: #f5f5f5;
    cursor: not-allowed;
  }
`;

const LoginButton = styled.button`
  width: 100%;
  padding: 12px 24px;
  background: #edf1f2;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }
`;

const InfoText = styled.div`
  margin-top: 20px;
  padding: 15px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 8px;
  color: #333;
  font-size: 14px;
  line-height: 1.4;
`;

function UserIdentityForm({ onLogin }) {
    const [username, setUsername] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!username.trim()) {
            toast.error('Please enter a username');
            return;
        }

        setIsLoading(true);

        try {
            const response = await apiService.login(username.trim());

            if (response.data.success) {
                toast.success(response.data.message);
                onLogin(response.data.user);
            } else {
                toast.error(response.data.error || 'Login failed');
            }
        } catch (error) {
            toast.error(error.message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <LoginContainer>
            <LoginCard>
                <Title>Keep your study projects</Title>
                <Subtitle>
                    Choose a name to save and revisit your filters. This prototype uses names for identification, without passwords.
                </Subtitle>

                <form onSubmit={handleSubmit}>
                    <InputGroup>
                        <Label htmlFor="username">Enter your name to continue:</Label>
                        <Input
                            id="username"
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="e.g., John Doe"
                            disabled={isLoading}
                            autoFocus
                        />
                    </InputGroup>

                    <LoginButton type="submit" disabled={isLoading}>
                        {isLoading ? 'Signing in...' : 'Continue to projects'}
                    </LoginButton>
                </form>

                <InfoText>
                    <strong>Features you'll explore:</strong><br />
                    • 3D visualization of Calgary buildings<br />
                    • Natural language queries (e.g., "buildings over 100 feet")<br />
                    • Save and load your map analyses<br />
                    • Interactive building information
                </InfoText>
            </LoginCard>
        </LoginContainer>
    );
}

export default UserIdentityForm;
