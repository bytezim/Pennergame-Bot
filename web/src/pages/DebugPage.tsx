import { useState, useEffect } from "react";
import {
  VStack,
  Text,
  Heading,
  Box,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  HStack,
  Badge,
} from "@chakra-ui/react";
import { DashboardCard } from "../components/DashboardCard";
import { FiDatabase, FiGlobe } from "react-icons/fi";
import { getApiUrl } from "../utils/api";

interface DbData {
  [tableName: string]: any[];
}

export const DebugPage = () => {
  const [htmlContent, setHtmlContent] = useState<string>("");
  const [dbData, setDbData] = useState<DbData>({});
  const [loadingHtml, setLoadingHtml] = useState(true);
  const [loadingDb, setLoadingDb] = useState(true);

  useEffect(() => {
    loadHtmlContent();
    loadDbData();
    // Refresh every 5 seconds
    const interval = setInterval(() => {
      loadHtmlContent();
      loadDbData();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadHtmlContent = async () => {
    try {
      const response = await fetch(getApiUrl("/request_html"));
      if (response.ok) {
        const data = await response.json();
        setHtmlContent(data.html || "Noch kein Request durchgeführt");
      }
    } catch (error) {
      console.error("Failed to load HTML content:", error);
    } finally {
      setLoadingHtml(false);
    }
  };

  const loadDbData = async () => {
    try {
      const response = await fetch(getApiUrl("/database/dump"));
      if (response.ok) {
        const data = await response.json();
        setDbData(data.tables || {});
      }
    } catch (error) {
      console.error("Failed to load database data:", error);
    } finally {
      setLoadingDb(false);
    }
  };

  const renderTableData = (tableName: string, rows: any[]) => {
    if (!rows || rows.length === 0) {
      return (
        <Text color="gray.400" textAlign="center" py={4}>
          Keine Daten in Tabelle "{tableName}"
        </Text>
      );
    }

    const columns = Object.keys(rows[0]);

    return (
      <Box overflowX="auto">
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              {columns.map((col) => (
                <Th key={col} color="teal.300" borderColor="whiteAlpha.300">
                  {col}
                </Th>
              ))}
            </Tr>
          </Thead>
          <Tbody>
            {rows.map((row, idx) => (
              <Tr key={idx}>
                {columns.map((col) => (
                  <Td key={col} color="gray.300" borderColor="whiteAlpha.200">
                    {typeof row[col] === "boolean"
                      ? row[col]
                        ? "✓"
                        : "✗"
                      : row[col]?.toString() || "-"}
                  </Td>
                ))}
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>
    );
  };

  return (
    <VStack align="stretch" spacing={6} className="fade-in">
      <Heading size="lg" color="white">
        Debug
      </Heading>

      {/* HTML Content from Last Request */}
      <DashboardCard title="Letzter Request HTML" icon={FiGlobe}>
        {loadingHtml ? (
          <HStack justify="center" py={8}>
            <Spinner color="teal.400" />
            <Text color="gray.400">Lade HTML-Inhalt...</Text>
          </HStack>
        ) : (
          <Box>
            <HStack mb={3}>
              <Badge colorScheme="teal">
                {htmlContent.length.toLocaleString()} Zeichen
              </Badge>
            </HStack>
            <Box
              border="1px solid"
              borderColor="whiteAlpha.300"
              borderRadius="md"
              overflow="hidden"
              bg="white"
            >
              <iframe
                srcDoc={htmlContent}
                style={{
                  width: "100%",
                  height: "600px",
                  border: "none",
                  backgroundColor: "white",
                }}
                sandbox="allow-same-origin"
                title="HTML Preview"
              />
            </Box>
          </Box>
        )}
      </DashboardCard>

      {/* SQLite Database Visualization */}
      <DashboardCard title="SQLite Datenbank" icon={FiDatabase}>
        {loadingDb ? (
          <HStack justify="center" py={8}>
            <Spinner color="teal.400" />
            <Text color="gray.400">Lade Datenbank-Inhalt...</Text>
          </HStack>
        ) : (
          <Tabs variant="enclosed" colorScheme="teal">
            <TabList>
              {Object.keys(dbData).map((tableName) => (
                <Tab key={tableName} color="gray.400" _selected={{ color: "white", bg: "teal.600" }}>
                  {tableName}
                  <Badge ml={2} colorScheme="teal">
                    {dbData[tableName].length}
                  </Badge>
                </Tab>
              ))}
              {Object.keys(dbData).length === 0 && (
                <Tab color="gray.400">Keine Tabellen</Tab>
              )}
            </TabList>

            <TabPanels>
              {Object.entries(dbData).map(([tableName, rows]) => (
                <TabPanel key={tableName} px={0}>
                  {renderTableData(tableName, rows)}
                </TabPanel>
              ))}
              {Object.keys(dbData).length === 0 && (
                <TabPanel>
                  <Text color="gray.400" textAlign="center" py={4}>
                    Keine Datenbank-Tabellen gefunden
                  </Text>
                </TabPanel>
              )}
            </TabPanels>
          </Tabs>
        )}
      </DashboardCard>
    </VStack>
  );
};
