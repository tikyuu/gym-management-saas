import {
  Stack,
  StackProps,
  aws_ec2 as ec2,
  aws_rds as rds,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface DatabaseStackProps extends StackProps {
  applicationName: string;
  databaseEngineVersion: string;
  databaseInstanceClass: string;
  databaseSubnetIds: string[];
  environmentName: string;
  rdsSecurityGroup: ec2.ISecurityGroup;
  vpc: ec2.IVpc;
}

export class DatabaseStack extends Stack {
  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    new rds.CfnDBSubnetGroup(this, "DatabaseSubnetGroup", {
      dbSubnetGroupDescription: "Subnet group for the RDS database",
      dbSubnetGroupName: `${resourceNamePrefix}-db-subnet-group`,
      subnetIds: props.databaseSubnetIds,
      tags: [
        {
          key: "Name",
          value: `${resourceNamePrefix}-db-subnet-group`,
        },
      ],
    });
  }
}
