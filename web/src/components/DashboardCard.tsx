import { Card, CardHeader, CardBody, Heading, HStack, Icon, Box } from "@chakra-ui/react";
import { IconType } from "react-icons";
import { ReactNode } from "react";

interface DashboardCardProps {
  title: string;
  icon: IconType;
  children: ReactNode;
  action?: ReactNode;
}

export const DashboardCard = ({ title, icon, children, action }: DashboardCardProps) => {
  return (
    <Card className="dashboard-card card-hover fade-in" bg="gray.800" borderColor="whiteAlpha.200">
      <CardHeader pb={3}>
        <HStack justify="space-between" align="center">
          <HStack spacing={3}>
            <Icon as={icon} boxSize={6} color="teal.400" />
            <Heading size="md" color="white" fontWeight="semibold">
              {title}
            </Heading>
          </HStack>
          {action && <Box>{action}</Box>}
        </HStack>
      </CardHeader>
      <CardBody pt={0}>{children}</CardBody>
    </Card>
  );
};
