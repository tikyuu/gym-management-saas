export const devConfig = {
  applicationName: "gym-management",
  environmentName: "dev",
  region: "ap-northeast-1",
  vpcCidr: "10.10.0.0/16",
  publicSubnets: [
    {
      id: "PublicSubnet1",
      name: "public-1a-subnet",
      availabilityZone: "ap-northeast-1a",
      cidrBlock: "10.10.1.0/24",
    },
    {
      id: "PublicSubnet2",
      name: "public-1c-subnet",
      availabilityZone: "ap-northeast-1c",
      cidrBlock: "10.10.2.0/24",
    },
  ],
  privateIngressSubnets: [
    {
      id: "PrivateIngressSubnet1",
      name: "private-ingress-1a-subnet",
      availabilityZone: "ap-northeast-1a",
      cidrBlock: "10.10.11.0/24",
    },
    {
      id: "PrivateIngressSubnet2",
      name: "private-ingress-1c-subnet",
      availabilityZone: "ap-northeast-1c",
      cidrBlock: "10.10.12.0/24",
    },
  ],
  applicationSubnets: [
    {
      id: "ApplicationSubnet1",
      name: "private-application-1a-subnet",
      availabilityZone: "ap-northeast-1a",
      cidrBlock: "10.10.21.0/24",
    },
    {
      id: "ApplicationSubnet2",
      name: "private-application-1c-subnet",
      availabilityZone: "ap-northeast-1c",
      cidrBlock: "10.10.22.0/24",
    },
  ],
  databaseSubnets: [
    {
      id: "DatabaseSubnet1",
      name: "private-database-1a-subnet",
      availabilityZone: "ap-northeast-1a",
      cidrBlock: "10.10.31.0/24",
    },
    {
      id: "DatabaseSubnet2",
      name: "private-database-1c-subnet",
      availabilityZone: "ap-northeast-1c",
      cidrBlock: "10.10.32.0/24",
    },
  ],
};
