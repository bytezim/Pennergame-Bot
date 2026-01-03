/**
 * Error boundary component for catching React errors.
 */
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Box, Button, Heading, Text, VStack } from '@chakra-ui/react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(_error: Error): Partial<State> {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('Error boundary caught error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Box
          minH="100vh"
          display="flex"
          alignItems="center"
          justifyContent="center"
          bg="gray.900"
          p={4}
        >
          <VStack
            spacing={4}
            maxW="600px"
            bg="gray.800"
            p={8}
            borderRadius="lg"
            boxShadow="xl"
          >
            <Heading color="red.400" size="lg">
              Oops! Something went wrong
            </Heading>
            
            <Text color="gray.300" textAlign="center">
              The application encountered an unexpected error. This has been logged for investigation.
            </Text>

            {this.state.error && (
              <Box
                w="100%"
                p={4}
                bg="gray.900"
                borderRadius="md"
                borderWidth="1px"
                borderColor="red.700"
                overflowX="auto"
              >
                <Text fontSize="sm" color="red.300" fontFamily="mono">
                  {this.state.error.toString()}
                </Text>
              </Box>
            )}

            <Button
              colorScheme="teal"
              onClick={this.handleReset}
              size="lg"
            >
              Try Again
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => window.location.reload()}
            >
              Reload Page
            </Button>
          </VStack>
        </Box>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook version for functional components.
 */
export function useErrorHandler(): (error: Error) => void {
  const [, setError] = React.useState();

  return React.useCallback(
    (error: Error) => {
      setError(() => {
        throw error;
      });
    },
    []
  );
}
