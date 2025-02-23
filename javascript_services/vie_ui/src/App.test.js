import { render, screen } from '@testing-library/react';
import App from './App';

/**
 * @test React App Render Test
 * Verifies that the React application renders correctly and contains expected elements.
 * 
 * @pre The App component is properly configured
 * @post The learn react link is present in the document
 */
test('renders learn react link', () => {
  render(<App />);
  const linkElement = screen.getByText(/learn react/i);
  expect(linkElement).toBeInTheDocument();
});
